"""AI emal dövrü — emal olunmamış xəbərləri GPT ilə 4 dilə çevirir.

İstifadə (backend/ qovluğundan):
    python -m app.agents.process_news           # 12 xəbər (default)
    python -m app.agents.process_news 50        # 50 xəbər
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.agents.llm import has_openai
from app.agents.news_ai import translate_and_rewrite
from app.db.session import AsyncSessionLocal, engine
from app.models import News

_CONCURRENCY = 4


async def _process_one(sem: asyncio.Semaphore, row_id: int, title: str,
                       summary: str | None) -> tuple[int, dict | None]:
    async with sem:
        return row_id, await translate_and_rewrite(title, summary)


async def process_pending(limit: int = 12) -> dict[str, int]:
    """Emal olunmamış xəbərləri GPT ilə emal edir. Sayğacları qaytarır."""
    async with AsyncSessionLocal() as session:
        rows = (
            await session.scalars(
                select(News)
                .where(News.is_processed.is_(False))
                .order_by(News.published_at.desc().nullslast())
                .limit(limit)
            )
        ).all()
        pending = [(n.id, n.title, n.summary) for n in rows]

    if not pending:
        return {"pending": 0, "processed": 0, "failed": 0}

    # GPT çağırışları paralel (sessiyadan kənar — təhlükəsiz).
    sem = asyncio.Semaphore(_CONCURRENCY)
    results = await asyncio.gather(
        *(_process_one(sem, rid, t, s) for rid, t, s in pending)
    )

    processed = 0
    ids = [row_id for row_id, tr in results if tr]
    async with AsyncSessionLocal() as session:
        by_id = {
            n.id: n
            for n in (
                await session.scalars(select(News).where(News.id.in_(ids)))
            ).all()
        }
        for row_id, tr in results:
            news = by_id.get(row_id)
            if not tr or news is None:
                continue
            news.translations = tr
            az = tr.get("az") or {}
            news.title_az = az.get("title")
            news.summary_az = az.get("body")
            news.is_processed = True
            processed += 1
        await session.commit()

    return {
        "pending": len(pending),
        "processed": processed,
        "failed": len(pending) - processed,
    }


async def main() -> None:
    if not has_openai():
        print("❌ OPENAI_API_KEY yoxdur (.env yoxla).")
        return
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    print(f"⏳ {limit} xəbər emal olunur (GPT)…")
    stats = await process_pending(limit)
    print(
        f"✅ Emal bitdi — cəhd: {stats['pending']}, "
        f"uğurlu: {stats['processed']}, uğursuz: {stats['failed']}"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
