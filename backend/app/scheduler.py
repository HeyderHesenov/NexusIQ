"""Cron planlayıcı (Addım 10) — saatlıq ingestion + hadisə əsaslı yeniləmə.

APScheduler (AsyncIOScheduler) FastAPI ilə eyni event loop-da işləyir.

Default dövr (PULSUZ):
  RSS çək → dedup → skorla → yeni xəbər olsa push göndər.

AI tərcümə (GPT, XƏRCLİ) yalnız SCHEDULER_AI_PROCESS=true olduqda işləyir —
gözlənilməz API xərcinin qarşısını alır.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings

logger = logging.getLogger("nexusiq.scheduler")

_scheduler: AsyncIOScheduler | None = None


async def ingest_cycle() -> None:
    """Bir planlı dövr: ingestion (+ opsional AI emal)."""
    # Gec import — başlanğıc dövrəsini sürətli saxlamaq üçün.
    from app.ingestion.run import ingest_once

    try:
        stats = await ingest_once()
        logger.info(
            "Planlı ingestion — yeni: %s, push: %s",
            stats.get("added", 0),
            stats.get("pushed", 0),
        )
    except Exception:  # noqa: BLE001
        logger.exception("Planlı ingestion xətası")
        return

    if settings.scheduler_ai_process and stats.get("added", 0) > 0:
        from app.agents.process_news import process_pending

        try:
            ai = await process_pending(settings.scheduler_ai_batch)
            logger.info("Planlı AI emal — emal olunan: %s", ai.get("processed", 0))
        except Exception:  # noqa: BLE001
            logger.exception("Planlı AI emal xətası")


def start_scheduler() -> None:
    """Planlayıcını qurur və işə salır (FastAPI startup-da)."""
    global _scheduler
    if not settings.scheduler_enabled:
        logger.info("Scheduler söndürülüb (SCHEDULER_ENABLED=false).")
        return
    if _scheduler is not None:
        return

    _scheduler = AsyncIOScheduler(timezone="UTC")
    minutes = max(5, settings.ingest_interval_minutes)
    _scheduler.add_job(
        ingest_cycle,
        trigger="interval",
        minutes=minutes,
        id="ingest_cycle",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler başladı — hər %s dəqiqədə ingestion.", minutes)


def shutdown_scheduler() -> None:
    """Planlayıcını dayandırır (FastAPI shutdown-da)."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler dayandı.")
