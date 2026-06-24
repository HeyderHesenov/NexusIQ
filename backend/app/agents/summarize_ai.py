"""AI xülasə — təsvirsiz xəbərlərə qısa, sadiq xülasə yazır (GPT, XƏRC).

Bəzi mənbələr (xüsusən Yahoo Finance) RSS-də `<description>` vermir → xəbər kartı
təsvirsiz/boş görünür. Bu modul belə xəbərlər üçün:
  1. məqalə səhifəsindən mətn çəkir (og:description + meta + ilk paraqraflar) — PULSUZ;
  2. GPT-yə YALNIZ bu kontekst + başlıq verir → 2-3 cümləlik sadiq xülasə (halüsinasiya
     riskini azaltmaq üçün uydurma rəqəm/fakt qadağan).
Xülasə `summary`-yə yazılır, tərcümə markerləri sıfırlanır → mövcud pulsuz tərcümə
(translate_free) onu 4 dilə çevirir.

İstifadə (backend/ qovluğundan):
    python -m app.agents.summarize_ai          # default batch
    python -m app.agents.summarize_ai 200       # 200 (köhnə backlog daxil)
    python -m app.agents.summarize_ai 200 all   # yaş limiti olmadan
"""
from __future__ import annotations

import asyncio
import logging
import re
import sys
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import or_, select

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models import News

logger = logging.getLogger("nexusiq.summarize")

_UA = {"User-Agent": "Mozilla/5.0 (NexusIQ news aggregator)"}
_CONCURRENCY = 6

_META = re.compile(
    r'<meta[^>]+(?:property|name)=["\'](?:og:description|twitter:description|description)["\']'
    r'[^>]*content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_META_REV = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*'
    r'(?:property|name)=["\'](?:og:description|twitter:description|description)["\']',
    re.IGNORECASE,
)
_P = re.compile(r"<p[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _clean(html: str) -> str:
    return _WS.sub(" ", _TAGS.sub(" ", html)).strip()


def _extract_context(html: str) -> str:
    """og:description + ilk bir neçə paraqrafdan məqalə konteksti (≤1800 simvol)."""
    parts: list[str] = []
    m = _META.search(html) or _META_REV.search(html)
    if m:
        parts.append(_clean(m.group(1)))
    for pm in _P.finditer(html):
        txt = _clean(pm.group(1))
        if len(txt) >= 40:  # naviqasiya/footer kiçik <p>-ləri atla
            parts.append(txt)
        if sum(len(p) for p in parts) > 1800:
            break
    ctx = " ".join(parts)
    return ctx[:1800].strip()


async def _fetch_context(client: httpx.AsyncClient, url: str) -> str:
    try:
        r = await client.get(url, timeout=15.0)
        r.raise_for_status()
        return _extract_context(r.text[:300_000])
    except (httpx.HTTPError, httpx.TimeoutException):
        return ""


_SYSTEM = (
    "You are a financial news editor for the NexusIQ terminal. Write a SHORT, "
    "factual summary (2-3 sentences) of the news item, in English, based ONLY on "
    "the provided headline and article context. Do NOT invent numbers, quotes, "
    "dates, tickers or facts that are not present. If the context is thin, write a "
    "neutral 1-2 sentence summary that restates the headline's claim WITHOUT "
    "fabricated specifics. Neutral, professional, no hype, no financial advice. "
    "Output ONLY the summary text."
)


async def _summarize(title: str, context: str) -> str | None:
    """GPT ilə sadiq qısa xülasə (mənbə dili = en). Xəta/boş → None."""
    from app.agents.llm import openai_client

    try:
        resp = await openai_client().chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {
                    "role": "user",
                    "content": f"HEADLINE: {title}\n\nARTICLE CONTEXT:\n{context or '(none)'}",
                },
            ],
            temperature=0.3,
            max_tokens=180,
        )
        out = (resp.choices[0].message.content or "").strip()
        return out or None
    except Exception:  # noqa: BLE001
        logger.warning("AI xülasə xətası: %s", title[:60])
        return None


async def summarize_pending(
    limit: int | None = None, max_age_days: int | None = None
) -> dict[str, int]:
    """Təsvirsiz xəbərlərə AI xülasə yazır. `max_age_days` verilsə yalnız son N gün."""
    if not (settings.ai_summary_enabled and settings.openai_api_key):
        return {"pending": 0, "summarized": 0}

    limit = limit or settings.ai_summary_batch
    empty = or_(News.summary.is_(None), News.summary == "")
    async with AsyncSessionLocal() as session:
        stmt = select(News).where(empty)
        if max_age_days is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
            stmt = stmt.where(News.published_at >= cutoff)
        stmt = stmt.order_by(News.published_at.desc().nullslast()).limit(limit)
        rows = (await session.scalars(stmt)).all()
        targets = [(n.id, n.title, n.url) for n in rows]

    if not targets:
        return {"pending": 0, "summarized": 0}

    sem = asyncio.Semaphore(_CONCURRENCY)

    async def work(row_id: int, title: str, url: str) -> tuple[int, str | None]:
        async with sem:
            async with httpx.AsyncClient(headers=_UA, follow_redirects=True) as cli:
                ctx = await _fetch_context(cli, url) if url else ""
            return row_id, await _summarize(title, ctx)

    results = await asyncio.gather(*(work(*t) for t in targets))

    summarized = 0
    by_id = {rid: s for rid, s in results if s}
    if by_id:
        async with AsyncSessionLocal() as session:
            rows = (
                await session.scalars(
                    select(News).where(News.id.in_(list(by_id)))
                )
            ).all()
            for n in rows:
                n.summary = by_id[n.id][:2000]
                # Tərcümə yenidən qurulsun (yeni body 4 dilə çevrilsin).
                n.translations = None
                n.title_az = None
                n.summary_az = None
                summarized += 1
            await session.commit()

    return {"pending": len(targets), "summarized": summarized}


async def summarize_all_pending(max_loops: int = 80) -> dict[str, int]:
    """Avtomatik dövr: yalnız son `ai_summary_max_age_days` günü drenaj edir."""
    if not (settings.ai_summary_enabled and settings.openai_api_key):
        return {"summarized": 0}
    total = 0
    for _ in range(max_loops):
        stats = await summarize_pending(max_age_days=settings.ai_summary_max_age_days)
        n = stats.get("summarized", 0)
        total += n
        if n == 0:
            break
    return {"summarized": total}


async def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else settings.ai_summary_batch
    age = None if (len(sys.argv) > 2 and sys.argv[2] == "all") else settings.ai_summary_max_age_days
    print(f"⏳ {limit} təsvirsiz xəbərə AI xülasə (age={age})…")
    stats = await summarize_pending(limit, max_age_days=age)
    print(f"✅ cəhd: {stats['pending']}, xülasə: {stats['summarized']}")
    # Yeni summary-ləri dərhal 4 dilə tərcümə et.
    from app.agents.translate_free import translate_all_pending

    tr = await translate_all_pending()
    print(f"✅ tərcümə: {tr.get('translated', 0)}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
