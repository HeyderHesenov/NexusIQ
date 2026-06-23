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

# Push olunmuş ekstremal anomaliyalar — dublikat bildirişin qarşısını alır.
# Element: "{asof}:{key}".
_pushed_anomalies: set[str] = set()


async def ingest_cycle() -> None:
    """Bir planlı dövr: ingestion (+ opsional AI emal) + anomaliya skanı."""
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
    else:
        if settings.scheduler_ai_process and stats.get("added", 0) > 0:
            from app.agents.process_news import process_pending

            try:
                ai = await process_pending(settings.scheduler_ai_batch)
                logger.info(
                    "Planlı AI emal — emal olunan: %s", ai.get("processed", 0)
                )
            except Exception:  # noqa: BLE001
                logger.exception("Planlı AI emal xətası")

    await _image_cycle()
    await _translate_cycle()
    await _embed_cycle()
    await _anomaly_cycle()


async def _image_cycle() -> None:
    """Şəkilsiz xəbərlərə naşirin og:image-ini doldurur (thumbnail)."""
    from app.ingestion.enrich_images import backfill

    try:
        stats = await backfill()
        if stats.get("found"):
            logger.info("Şəkil backfill — %s xəbər", stats["found"])
    except Exception:  # noqa: BLE001
        logger.exception("Şəkil backfill xətası")


async def _translate_cycle() -> None:
    """Tərcüməsiz xəbərləri PULSUZ 4 dilə tərcümə edir (GPT-dən asılı deyil)."""
    if not settings.free_translate_enabled:
        return
    from app.agents.translate_free import translate_pending

    try:
        stats = await translate_pending()
        if stats.get("translated"):
            logger.info("Pulsuz tərcümə — %s xəbər", stats["translated"])
    except Exception:  # noqa: BLE001
        logger.exception("Pulsuz tərcümə xətası")


async def _embed_cycle() -> None:
    """Embedding-siz yeni xəbərləri embed edir (Tarixi Analoq motoru üçün)."""
    if not settings.embed_enabled:
        return
    from app.analytics.backfill_embeddings import embed_pending

    try:
        stats = await embed_pending()
        if stats.get("embedded"):
            logger.info("Xəbər embedding — %s xəbər", stats["embedded"])
            from app.analytics import analog

            analog.reset_index()  # yeni embedding-lər indeksə daxil olsun
    except Exception:  # noqa: BLE001
        logger.exception("Xəbər embedding xətası")


async def _anomaly_cycle() -> None:
    """Anomaliya skanı; yeni ekstremal → web push (PULSUZ, AI yox)."""
    from app.analytics import anomaly

    try:
        found = await anomaly.scan_all(force=True)
    except Exception:  # noqa: BLE001
        logger.exception("Anomaliya skanı xətası")
        return

    extreme_new = [
        a for a in found
        if a["severity"] == "extreme"
        and f"{a['asof']}:{a['key']}" not in _pushed_anomalies
    ]
    logger.info(
        "Anomaliya skanı — tapılan: %s, yeni ekstremal: %s",
        len(found), len(extreme_new),
    )
    if not extreme_new:
        return

    from app.db.session import AsyncSessionLocal
    from app.services import push_service

    async with AsyncSessionLocal() as session:
        for a in extreme_new:
            payload = push_service.build_anomaly_payload(
                a["label"], a["change_pct"], a["price_z"]
            )
            try:
                await push_service.send_to_all(session, payload)
                _pushed_anomalies.add(f"{a['asof']}:{a['key']}")
            except Exception:  # noqa: BLE001
                logger.exception("Anomaliya push xətası: %s", a["key"])


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
