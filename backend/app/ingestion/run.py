"""Xəbər ingestion-u işə salır: çək → dedup → bazaya yaz.

İstifadə (backend/ qovluğundan):
    python -m app.ingestion.run
"""
from __future__ import annotations

import asyncio

from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.ingestion.rss_collector import collect_all
from app.models import News
from app.services import push_service
from app.services.news_service import store_news


async def ingest_once() -> dict[str, int]:
    """Bir ingestion dövrü. Sayğac qaytarır + yeni xəbər olsa push göndərir.

    Yeni xəbərlər saxlandıqdan SONRA dərhal 4 dilə tərcümə olunur (drenaj) ki,
    heç bir xəbər UI-də tərcüməsiz (orijinal ingiliscə) görünməsin — bu, manual
    və planlı ingestion-un hər ikisini əhatə edir.
    """
    items = await collect_all()
    async with AsyncSessionLocal() as session:
        # Store-dan ƏVVƏLki ən böyük id — təzə əlavə olunanları (id > prev) ayırd etmək
        # üçün. Şəkil backfill əvvəlcə məhz bu təzə batch-ı hədəfləyir (lag pəncərəsi yox).
        prev_max_id = (await session.scalar(select(func.max(News.id)))) or 0
        stats = await store_news(session, items)
        if stats.get("added", 0) > 0:
            latest = await session.scalar(
                select(News.title).order_by(News.id.desc()).limit(1)
            )
            payload = push_service.build_news_payload(latest or "", stats["added"])
            push_stats = await push_service.send_to_all(session, payload)
            stats["pushed"] = push_stats["sent"]

    if stats.get("added", 0) > 0:
        from app.agents.summarize_ai import summarize_all_pending
        from app.agents.translate_free import translate_all_pending
        from app.ingestion.enrich_images import backfill as image_backfill

        # Təsvirsiz yeni xəbərlərə AI xülasə (tərcümədən ƏVVƏL ki, yeni body də
        # 4 dilə çevrilsin).
        stats["summarized"] = (await summarize_all_pending()).get("summarized", 0)
        stats["translated"] = (await translate_all_pending()).get("translated", 0)
        # Şəkilsiz yeni xəbərlərə naşirin og:image-ini doldur — manual ingest də
        # thumbnail-li olsun (scheduler dövrünü gözləmədən). ƏVVƏLcə təzə batch
        # (id > prev_max_id) — ən yeni xəbərlər saniyələr içində şəkil alsın; SONRA
        # qalan köhnə backloq. Backfill dayanıqlıdır (bir pis URL batch-i çökürtmür).
        fresh = (await image_backfill(since_id=prev_max_id)).get("found", 0)
        backlog = (await image_backfill()).get("found", 0)
        stats["images"] = fresh + backlog
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
