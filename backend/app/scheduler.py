"""Cron planlayıcı (Addım 10) — saatlıq ingestion + hadisə əsaslı yeniləmə.

APScheduler (AsyncIOScheduler) FastAPI ilə eyni event loop-da işləyir.

Default dövr (PULSUZ):
  RSS çək → dedup → skorla → yeni xəbər olsa push göndər.

AI tərcümə (AI, XƏRCLİ) yalnız SCHEDULER_AI_PROCESS=true olduqda işləyir —
gözlənilməz API xərcinin qarşısını alır.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings

logger = logging.getLogger("nexusiq.scheduler")

_scheduler: AsyncIOScheduler | None = None

# Push olunmuş ekstremal anomaliyalar — dublikat bildirişin qarşısını alır.
# Element: "{asof}:{key}".
_pushed_anomalies: set[str] = set()
# Tavan: `asof` hər skanda dəyişir, yəni açar sonsuz yeni olur və set proses
# ömrü boyu böyüyürdü (yavaş, amma sərhədsiz). Dublikat qorusu üçün yalnız
# YAXIN keçmiş lazımdır — tavan aşılanda ən köhnə yarısı atılır.
_PUSHED_MAX = 2000


def _remember_pushed(marker: str) -> None:
    """Push damğasını yadda saxla, seti tavanda tut (FIFO-vari)."""
    _pushed_anomalies.add(marker)
    if len(_pushed_anomalies) > _PUSHED_MAX:
        # Set sırasızdır; `asof` prefiksi ISO vaxt olduğu üçün leksik sıralama
        # xronoloji sıralama deməkdir → ən köhnələri at.
        for old in sorted(_pushed_anomalies)[: _PUSHED_MAX // 2]:
            _pushed_anomalies.discard(old)


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
                # Planlayıcı xərci qlobal cap-a sayılır (hər xəbər ~3 LLM: tərcümə+xülasə+kat).
                from app.core import budget

                await budget.record_system_usage(
                    "scheduler.process", ai.get("processed", 0) * 3
                )
            except Exception:  # noqa: BLE001
                logger.exception("Planlı AI emal xətası")

    # Yeni xəbərlər ingest_once daxilində drenaj olunur. Burada da çağırırıq ki,
    # keçən dövrdə gtx uğursuzluğundan tərcüməsiz qalan elementlər retry olunsun
    # (boşdursa ucuz — dərhal pending:0 qaytarır). Self-healing.
    await _summary_cycle()
    await _translate_cycle()
    await _image_cycle()
    await _embed_cycle()
    await _link_cycle()
    await _score_cycle()
    await _anomaly_cycle()
    await _maintenance_cycle()


async def _maintenance_cycle() -> None:
    """Auth sessiya + ai_usage retention təmizliyi (ucuz, idempotent DELETE)."""
    from app.core import budget
    from app.db.session import AsyncSessionLocal
    from app.services import auth_service

    try:
        async with AsyncSessionLocal() as session:
            sess_n = await auth_service.cleanup_sessions(session)
            usage_n = await budget.cleanup_usage(session)
        if sess_n or usage_n:
            logger.info("Təmizlik — sessiya: %s, ai_usage: %s", sess_n, usage_n)
    except Exception:  # noqa: BLE001
        logger.exception("Təmizlik dövrü xətası")


async def _summary_cycle() -> None:
    """Təsvirsiz son xəbərlərə AI xülasə (yalnız ai_summary_max_age_days günü)."""
    from app.agents.summarize_ai import summarize_all_pending

    try:
        stats = await summarize_all_pending()
        if stats.get("summarized"):
            logger.info("AI xülasə — %s xəbər", stats["summarized"])
            from app.core import budget

            await budget.record_system_usage("scheduler.summary", stats["summarized"])
    except Exception:  # noqa: BLE001
        logger.exception("AI xülasə dövrü xətası")


async def _translate_cycle() -> None:
    """Tərcüməsiz + keçmiş "İngiliscə kilidlənmiş" xəbərləri retry edir."""
    from app.agents.translate_free import retranslate_stale, translate_all_pending

    try:
        await translate_all_pending()
        await retranslate_stale()
    except Exception:  # noqa: BLE001
        logger.exception("Tərcümə dövrü xətası")


async def _image_cycle() -> None:
    """Şəkilsiz xəbərlərə naşirin og:image-ini doldurur (thumbnail)."""
    from app.ingestion.enrich_images import backfill

    try:
        stats = await backfill()
        if stats.get("found"):
            logger.info("Şəkil backfill — %s xəbər", stats["found"])
    except Exception:  # noqa: BLE001
        logger.exception("Şəkil backfill xətası")

    # Thumbnail proksi keşi öz-özünə dayanmır → həcm tavanını burada tətbiq et.
    try:
        from app.services import img_cache

        if removed := await img_cache.prune():
            logger.info("Şəkil keşi budandı — %s fayl", removed)
    except Exception:  # noqa: BLE001
        logger.exception("Şəkil keşi budama xətası")


async def _wait_for_db(attempts: int = 10, delay: float = 3.0) -> bool:
    """DB hazır olana qədər qısa gözlə (SELECT 1). Backend DB-dən əvvəl qalxsa
    (məs. pg 5433 hələ start olur), startup tutması səssiz uğursuz olmasın —
    hazır olanda bütün fazalar (xülasə/tərcümə/şəkil) işləsin. False = hələ hazır
    deyil (planlı dövr onsuz da sonra tutacaq)."""
    import asyncio

    from sqlalchemy import text

    from app.db.session import AsyncSessionLocal

    for _ in range(attempts):
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:  # noqa: BLE001
            await asyncio.sleep(delay)
    return False


async def startup_catchup() -> None:
    """Başlanğıc tutması — restart-dan sonra interval gözləmədən tərcüməsiz
    backlog-u + keçmiş kilidlənmiş İngiliscəni + şəkilsizliyi dərhal təmizləyir
    (scheduler-in ilk planlı dövrü ~2 dəq sonra başlayır)."""
    from app.agents.summarize_ai import summarize_all_pending
    from app.agents.translate_free import retranslate_stale, translate_all_pending
    from app.ingestion.enrich_images import backfill as image_backfill

    if not await _wait_for_db():
        logger.warning("Başlanğıc tutması: DB hazır deyil — planlı dövr sonra tutacaq")
        return

    try:
        summ = await summarize_all_pending()
        if summ.get("summarized"):
            logger.info("Başlanğıc AI xülasə — %s xəbər", summ["summarized"])
    except Exception:  # noqa: BLE001
        logger.exception("Başlanğıc AI xülasə xətası")

    try:
        stats = await translate_all_pending()
        if stats.get("translated"):
            logger.info("Başlanğıc tərcümə tutması — %s xəbər", stats["translated"])
        stale = await retranslate_stale()
        if stale.get("reset"):
            logger.info("Başlanğıc kilid bərpası — %s xəbər", stale["reset"])
    except Exception:  # noqa: BLE001
        logger.exception("Başlanğıc tərcümə xətası")

    try:
        img = await image_backfill()
        if img.get("found"):
            logger.info("Başlanğıc şəkil tutması — %s xəbər", img["found"])
    except Exception:  # noqa: BLE001
        logger.exception("Başlanğıc şəkil xətası")


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
            from app.core import budget

            await budget.record_system_usage("scheduler.embed", stats["embedded"])
            analog.reset_index()  # yeni embedding-lər indeksə daxil olsun
    except Exception:  # noqa: BLE001
        logger.exception("Xəbər embedding xətası")


async def _link_cycle() -> None:
    """Son xəbərlərdə xəbər↔aktiv detected linklərini tamamlayır (self-heal, AI YOX).

    İngest hook əsas işi görür; bu yalnız qaçanları (məs. flush xətası, feature-dən
    əvvəlki köhnə xəbər) tutur. Məhdud pəncərə → ucuz."""
    from app.db.session import AsyncSessionLocal
    from app.services import link_service

    try:
        async with AsyncSessionLocal() as session:
            linked = await link_service.self_heal_recent(session)
        if linked:
            logger.info("Link self-heal — %s yeni link", linked)
    except Exception:  # noqa: BLE001
        logger.exception("Link self-heal dövrü xətası")


async def _score_cycle() -> None:
    """Üfüqü bağlanmış forecast linklərini real qiymətlə balla (PULSUZ, LLM yox)."""
    if not settings.scorer_enabled:
        return
    from app.analytics import forecast_scorer

    try:
        stats = await forecast_scorer.score_pending()
        if stats.get("scored"):
            logger.info("Proqnoz doğruluq — %s link balandı", stats["scored"])
    except Exception:  # noqa: BLE001
        logger.exception("Proqnoz scorer dövrü xətası")


async def _anomaly_cycle() -> None:
    """Anomaliya skanı; yeni ekstremal → web push (PULSUZ, AI yox)."""
    from app.analytics import anomaly

    try:
        scan = await anomaly.scan_all(force=True)
    except Exception:  # noqa: BLE001
        logger.exception("Anomaliya skanı xətası")
        return

    found = scan.get("anomalies", [])
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
                _remember_pushed(f"{a['asof']}:{a['key']}")
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
        # İlk dövr boot-dan ~2 dəq sonra — uzun fasilədən sonra xəbər boşluğu
        # 60 dəq yox, dəqiqələr içində dolsun (startup_catchup ilə yarışmasın).
        next_run_time=datetime.now(timezone.utc) + timedelta(seconds=120),
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
