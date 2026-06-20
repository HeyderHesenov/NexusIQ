"""Sağlamlıq yoxlaması — sistem və DB statusu."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    """Tətbiqin işlədiyini təsdiqləyir."""
    return {"status": "ok", "app": settings.app_name, "env": settings.environment}


@router.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)) -> dict:
    """DB bağlantısını yoxlayır."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "database": "unreachable", "detail": str(exc)}
