"""Web Push route-ları — VAPID açarı, abunə, test bildirişi."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.services import push_service

router = APIRouter()


class SubKeys(BaseModel):
    p256dh: str
    auth: str


class SubscribeRequest(BaseModel):
    endpoint: str = Field(..., min_length=10)
    keys: SubKeys
    lang: str = "az"


class EndpointRequest(BaseModel):
    endpoint: str = Field(..., min_length=10)


@router.get("/key")
async def vapid_key() -> dict:
    """Frontend-in abunə üçün istifadə edəcəyi public VAPID açarı."""
    return {"publicKey": settings.vapid_public_key, "enabled": settings.push_enabled}


@router.post("/subscribe")
async def subscribe(
    req: SubscribeRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Brauzer abunəsini saxlayır (upsert)."""
    await push_service.save_subscription(
        db,
        endpoint=req.endpoint,
        p256dh=req.keys.p256dh,
        auth=req.keys.auth,
        lang=req.lang,
    )
    return {"ok": True}


@router.post("/unsubscribe")
async def unsubscribe(
    req: EndpointRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Abunəni silir."""
    await push_service.delete_subscription(db, req.endpoint)
    return {"ok": True}


@router.post("/test")
async def test_push(db: AsyncSession = Depends(get_db)) -> dict:
    """Bütün abunələrə test bildirişi göndərir (yoxlama üçün)."""
    payload = {
        "title": "NexusIQ ✅",
        "body": "Bildirişlər işləyir! Artıq yeni xəbərdən xəbərdar olacaqsan.",
        "url": "/",
        "tag": "nexusiq-test",
    }
    stats = await push_service.send_to_all(db, payload)
    return {"ok": True, **stats}
