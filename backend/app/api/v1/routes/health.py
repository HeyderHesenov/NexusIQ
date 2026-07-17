"""Sağlamlıq yoxlaması — sistem və DB statusu."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

router = APIRouter()
logger = logging.getLogger("nexusiq.health")


@router.get("/health")
async def health() -> dict:
    """Tətbiqin işlədiyini təsdiqləyir.

    `env` sahəsi QƏSDƏN yoxdur — anonim sorğuya deployment mühitini demək
    lazımsız kəşfiyyatdır (hücumçuya dev/prod fərqini, deməli hansı qapıların
    açıq ola biləcəyini deyir). İstifadəçilər: `status.sh` yalnız `"status":"ok"`
    axtarır, `dev.sh`/`watchdog.sh` isə sadəcə HTTP uğurunu — yoxlanıldı.
    """
    return {"status": "ok", "app": settings.app_name}


@router.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)) -> dict:
    """DB bağlantısını yoxlayır."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:  # noqa: BLE001 — detalı sızdırma, server-side logla
        logger.warning("DB sağlamlıq yoxlaması uğursuz", exc_info=True)
        return {"status": "error", "database": "unreachable"}
