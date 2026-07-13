"""Məqalə mətni backfill — `content` boş olan xəbərlər üçün paraqrafları çəkir.

Naşirin səhifəsindən <p> mətnlərini götürür (tam mətnin bir hissəsi).
İstifadə (backend/ qovluğundan):
    python -m app.ingestion.enrich_content
"""
from __future__ import annotations

import asyncio
import html
import re

import httpx
from sqlalchemy import select

from app.core import netguard
from app.db.session import AsyncSessionLocal, engine
from app.models import News

_UA = {"User-Agent": "Mozilla/5.0 (NexusIQ news aggregator)"}
_CONCURRENCY = 8
_MAX_CHARS = 2400

_TAG = re.compile(r"<[^>]+>")
_P = re.compile(r"<p\b[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
_SCRIPT = re.compile(r"<(script|style)\b.*?</\1>", re.IGNORECASE | re.DOTALL)


def _clean(fragment: str) -> str:
    txt = _TAG.sub("", fragment)
    txt = html.unescape(txt)
    return re.sub(r"\s+", " ", txt).strip()


def _extract(page: str) -> str | None:
    page = _SCRIPT.sub("", page)
    paras: list[str] = []
    for m in _P.finditer(page):
        t = _clean(m.group(1))
        # qısa naviqasiya/cookie cümlələrini at
        if len(t) < 60:
            continue
        paras.append(t)
        if sum(len(p) for p in paras) >= _MAX_CHARS:
            break
    if not paras:
        return None
    return "\n\n".join(paras)[:_MAX_CHARS]


async def _fetch(sem, client, row_id, url):
    async with sem:
        try:
            # SSRF-təhlükəsiz — daxili/metadata ünvanlara redirect bloklanır.
            r = await netguard.safe_get(client, url, timeout=15.0)
            if r is None:
                return row_id, None
            r.raise_for_status()
            # CPU-tutumlu HTML parse-ı thread-ə ver — event loop bloklanmasın.
            text = await asyncio.to_thread(_extract, r.text[:400_000])
            return row_id, text
        except (httpx.HTTPError, httpx.TimeoutException):
            return row_id, None


async def backfill(limit: int = 300) -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        rows = (
            await session.scalars(
                select(News)
                .where(News.content.is_(None))
                .order_by(News.published_at.desc().nullslast())
                .limit(limit)
            )
        ).all()
        targets = [(n.id, n.url) for n in rows]

    if not targets:
        return {"checked": 0, "found": 0}

    sem = asyncio.Semaphore(_CONCURRENCY)
    async with httpx.AsyncClient(headers=_UA, follow_redirects=False) as client:
        results = await asyncio.gather(
            *(_fetch(sem, client, rid, url) for rid, url in targets)
        )

    found = 0
    ids = [rid for rid, text in results if text]
    async with AsyncSessionLocal() as session:
        by_id = {
            n.id: n
            for n in (
                await session.scalars(select(News).where(News.id.in_(ids)))
            ).all()
        }
        for row_id, text in results:
            news = by_id.get(row_id)
            if not text or news is None:
                continue
            news.content = text
            found += 1
        await session.commit()
    return {"checked": len(targets), "found": found}


async def _main() -> None:
    res = await backfill()
    await engine.dispose()
    print(res)


if __name__ == "__main__":
    asyncio.run(_main())
