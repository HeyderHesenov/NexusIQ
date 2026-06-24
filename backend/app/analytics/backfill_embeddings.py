"""Xəbərlərə embedding yazır — Tarixi Analoq motoru üçün.

text-embedding-3-small (app/rag/embed.py). Həm birdəfəlik backfill, həm də
scheduler hook (`embed_pending`) bunu işlədir.

İstifadə (backend/ qovluğundan):
    python -m app.analytics.backfill_embeddings          # default batch
    python -m app.analytics.backfill_embeddings 500      # 500 xəbər
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.agents.llm import has_openai
from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.models import News
from app.rag import embed


def _text(title: str, summary: str | None) -> str:
    """Embedding üçün mətn — başlıq + xülasə (orijinal dil, ən zəngin siqnal)."""
    return f"{title}. {summary}".strip() if summary else title


async def embed_pending(limit: int | None = None) -> dict[str, int]:
    """embedding IS NULL olan ən təzə xəbərləri embed edib yazır."""
    if not settings.embed_enabled or not has_openai():
        return {"pending": 0, "embedded": 0}

    limit = limit or settings.embed_batch
    async with AsyncSessionLocal() as session:
        rows = (
            await session.scalars(
                select(News)
                .where(News.embedding.is_(None))
                .order_by(News.published_at.desc().nullslast())
                .limit(limit)
            )
        ).all()
        pending = [(n.id, n.title, n.summary) for n in rows]

    if not pending:
        return {"pending": 0, "embedded": 0}

    vectors = await embed.embed_texts([_text(t, s) for _, t, s in pending])

    embedded = 0
    ids = [row_id for row_id, _, _ in pending]
    async with AsyncSessionLocal() as session:
        by_id = {
            n.id: n
            for n in (
                await session.scalars(select(News).where(News.id.in_(ids)))
            ).all()
        }
        for (row_id, _, _), vec in zip(pending, vectors):
            news = by_id.get(row_id)
            if news is None:
                continue
            news.embedding = [round(float(x), 6) for x in vec.tolist()]
            embedded += 1
        await session.commit()

    return {"pending": len(pending), "embedded": embedded}


async def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    total = 0
    while True:
        stats = await embed_pending(min(limit - total, settings.embed_batch) or settings.embed_batch)
        if stats["embedded"] == 0:
            break
        total += stats["embedded"]
        print(f"  embed olundu: {total}")
        if total >= limit:
            break
    print(f"✅ Bitdi — embed olunan: {total}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
