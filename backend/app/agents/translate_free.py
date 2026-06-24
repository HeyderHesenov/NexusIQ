"""Pulsuz maşın tərcüməsi — xəbərləri 4 dilə SADİQ tərcümə edir.

Google-ın açarsız (gtx) tərcümə endpoint-i, httpx ilə. API xərci YOXDUR.
GPT-dən fərqli olaraq mətni yenidən YAZMIR — orijinalı olduğu kimi tərcümə edir
(istifadəçi tələbi: "xəbərin texti dəyişilməsin, sadəcə dilə uyğunlaşsın").

İstifadə (backend/ qovluğundan):
    python -m app.agents.translate_free        # 12 xəbər backfill
    python -m app.agents.translate_free 100    # 100 xəbər
"""
from __future__ import annotations

import asyncio
import sys

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models import News

LANGS = ("az", "en", "ru", "tr")
_URL = "https://translate.googleapis.com/translate_a/single"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NexusIQ/1.0)"}
_MAX_CHARS = 4800  # endpoint limiti


async def _translate_one(client: httpx.AsyncClient, text: str, target: str) -> str:
    """Bir mətni hədəf dilə tərcümə. Xəta olarsa orijinalı qaytarır."""
    if not text:
        return text
    try:
        r = await client.get(
            _URL,
            params={
                "client": "gtx",
                "sl": "auto",
                "tl": target,
                "dt": "t",
                "q": text[:_MAX_CHARS],
            },
        )
        r.raise_for_status()
        data = r.json()
        # Cavab: [[["tərcümə","orijinal",...], ...], ...]
        return "".join(seg[0] for seg in data[0] if seg and seg[0]) or text
    except (httpx.HTTPError, ValueError, IndexError, KeyError, TypeError):
        return text


async def translate_news(
    title: str, summary: str | None, source_lang: str = "en"
) -> dict[str, dict[str, str]]:
    """title + summary → {lang: {title, body}} (4 dil). Mənbə dil tərcümə olunmur."""
    out: dict[str, dict[str, str]] = {}
    async with httpx.AsyncClient(timeout=12.0, headers=_HEADERS) as client:
        for lang in LANGS:
            if lang == source_lang:
                out[lang] = {"title": title, "body": summary or ""}
                continue
            t = await _translate_one(client, title, lang)
            b = await _translate_one(client, summary or "", lang)
            out[lang] = {"title": t, "body": b}
    return out


async def translate_pending(limit: int | None = None) -> dict[str, int]:
    """Tərcüməsiz xəbərləri pulsuz tərcümə edir.

    `title_az IS NULL` həm translations=NULL, həm də boş translations={} olan
    xəbərləri tutur (köhnə ingestion bəzi sətirləri boş dict ilə yaratmışdı).
    """
    limit = limit or settings.free_translate_batch
    async with AsyncSessionLocal() as session:
        rows = (
            await session.scalars(
                select(News)
                .where(News.title_az.is_(None))
                .order_by(News.published_at.desc().nullslast())
                .limit(limit)
            )
        ).all()
        pending = [(n.id, n.title, n.summary, n.language) for n in rows]

    if not pending:
        return {"pending": 0, "translated": 0}

    translated = 0
    ids = [row_id for row_id, _, _, _ in pending]
    async with AsyncSessionLocal() as session:
        by_id = {
            n.id: n
            for n in (
                await session.scalars(select(News).where(News.id.in_(ids)))
            ).all()
        }
        for row_id, title, summary, lang in pending:
            news = by_id.get(row_id)
            if news is None:
                continue
            tr = await translate_news(title, summary, source_lang=lang or "en")
            news.translations = tr
            az = tr.get("az") or {}
            news.title_az = az.get("title")
            news.summary_az = az.get("body")
            translated += 1
        await session.commit()

    return {"pending": len(pending), "translated": translated}


async def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else settings.free_translate_batch
    print(f"⏳ {limit} xəbər pulsuz tərcümə olunur (Google free)…")
    stats = await translate_pending(limit)
    print(f"✅ Bitdi — cəhd: {stats['pending']}, tərcümə: {stats['translated']}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
