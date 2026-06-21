"""Xəbər ingestion-u işə salır: çək → dedup → bazaya yaz.

İstifadə (backend/ qovluğundan):
    python -m app.ingestion.run
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal, engine
from app.ingestion.rss_collector import collect_all
from app.models import News
from app.services import push_service
from app.services.news_service import store_news


async def ingest_once() -> dict[str, int]:
    """Bir ingestion dövrü. Sayğac qaytarır + yeni xəbər olsa push göndərir."""
    items = await collect_all()
    async with AsyncSessionLocal() as session:
        stats = await store_news(session, items)
        if stats.get("added", 0) > 0:
            latest = await session.scalar(
                select(News.title).order_by(News.id.desc()).limit(1)
            )
            payload = push_service.build_news_payload(latest or "", stats["added"])
            push_stats = await push_service.send_to_all(session, payload)
            stats["pushed"] = push_stats["sent"]
        return stats


async def main() -> None:
    stats = await ingest_once()
    print(
        f"✅ Ingestion bitdi — çəkilən: {stats['fetched']}, "
        f"yeni: {stats['added']}, dublikat: {stats['skipped']}"
    )
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
