"""Mövcud xəbərlərə sentiment + impact skoru yazır (birdəfəlik backfill).

İstifadə (backend/ qovluğundan):
    python -m app.analytics.backfill_scores          # yalnız boş olanlar
    python -m app.analytics.backfill_scores --all    # hamısını yenidən balla
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.analytics.scoring import score_text
from app.db.session import AsyncSessionLocal, engine
from app.models import News


async def backfill(force: bool = False) -> dict[str, int]:
    async with AsyncSessionLocal() as session:
        stmt = select(News)
        if not force:
            stmt = stmt.where(News.impact_score.is_(None))
        rows = (await session.scalars(stmt)).all()
        for n in rows:
            n.sentiment, n.impact_score = score_text(n.title, n.summary, n.category)
        await session.commit()
        return {"updated": len(rows)}


async def main() -> None:
    force = "--all" in sys.argv
    stats = await backfill(force)
    print(f"✅ Skor backfill bitdi — yenilənən: {stats['updated']}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
