"""Web Push route-ları — VAPID açarı, abunə, test bildirişi."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.ratelimit import rate_limit
from app.db.session import get_db
from app.services import push_service

router = APIRouter()

# Anonim yazma endpoint-ləri — abunə flood-una qarşı per-IP limit.
_push_limit = rate_limit("push", limit=20, window=60.0)


class SubKeys(BaseModel):
    p256dh: str = Field(..., max_length=200)
    auth: str = Field(..., max_length=100)


class SubscribeRequest(BaseModel):
    endpoint: str = Field(..., min_length=10, max_length=500)
    keys: SubKeys
    lang: str = Field("az", max_length=8)

    @field_validator("endpoint")
    @classmethod
    def _https_endpoint(cls, v: str) -> str:
        if not v.startswith("https://"):
            raise ValueError("endpoint https:// ilə başlamalıdır")
        return v


class EndpointRequest(BaseModel):
    endpoint: str = Field(..., min_length=10, max_length=500)


@router.get("/key")
async def vapid_key() -> dict:
    """Frontend-in abunə üçün istifadə edəcəyi public VAPID açarı."""
    return {"publicKey": settings.vapid_public_key, "enabled": settings.push_enabled}


@router.post("/subscribe", dependencies=[Depends(_push_limit)])
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


@router.post("/unsubscribe", dependencies=[Depends(_push_limit)])
async def unsubscribe(
    req: EndpointRequest, db: AsyncSession = Depends(get_db)
) -> dict:
    """Abunəni silir."""
    await push_service.delete_subscription(db, req.endpoint)
    return {"ok": True}


@router.post("/test")
async def test_push(db: AsyncSession = Depends(get_db)) -> dict:
    """Bütün abunələrə test bildirişi göndərir (yalnız development)."""
    if settings.environment != "development":
        raise HTTPException(status_code=404, detail="Not Found")
    payload = {
        "title": "NexusIQ ✅",
        "body": "Bildirişlər işləyir! Artıq yeni xəbərdən xəbərdar olacaqsan.",
        "url": "/",
        "tag": "nexusiq-test",
    }
    stats = await push_service.send_to_all(db, payload)
    return {"ok": True, **stats}
