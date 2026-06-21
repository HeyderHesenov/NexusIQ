"""Web Push xidməti — abunə saxla/sil + bildiriş göndər (pywebpush)."""
from __future__ import annotations

import json
import logging

from pywebpush import WebPushException, webpush
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import PushSubscription

logger = logging.getLogger("nexusiq.push")

# Endpoint cavabı bu kodlarla gəlsə abunə ölüdür — bazadan silinir.
_DEAD_STATUS = {404, 410}


async def save_subscription(
    session: AsyncSession, *, endpoint: str, p256dh: str, auth: str, lang: str = "az"
) -> PushSubscription:
    """Abunəni yaradır və ya yeniləyir (endpoint üzrə upsert)."""
    existing = await session.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )
    if existing is not None:
        existing.p256dh = p256dh
        existing.auth = auth
        existing.lang = lang
        sub = existing
    else:
        sub = PushSubscription(endpoint=endpoint, p256dh=p256dh, auth=auth, lang=lang)
        session.add(sub)
    await session.commit()
    return sub


async def delete_subscription(session: AsyncSession, endpoint: str) -> None:
    """Abunəni endpoint üzrə silir (idempotent)."""
    await session.execute(
        delete(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )
    await session.commit()


def _send_raw(sub: PushSubscription, payload: dict) -> int | None:
    """Tək abunəyə göndərir. Ölü abunə üçün status kodu qaytarır, yoxsa None."""
    try:
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
            ttl=86400,
        )
        return None
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in _DEAD_STATUS:
            return status
        logger.warning("Push göndərmə xətası: %s", exc)
        return None


async def send_to_all(session: AsyncSession, payload: dict) -> dict[str, int]:
    """Bütün abunələrə göndərir. Ölü abunələri təmizləyir. Sayğac qaytarır."""
    if not settings.push_enabled:
        logger.info("Push deaktiv (VAPID açarları yoxdur) — atlanır.")
        return {"sent": 0, "removed": 0, "total": 0}

    subs = (await session.scalars(select(PushSubscription))).all()
    sent = 0
    dead_endpoints: list[str] = []
    for sub in subs:
        status = _send_raw(sub, payload)
        if status in _DEAD_STATUS:
            dead_endpoints.append(sub.endpoint)
        else:
            sent += 1

    if dead_endpoints:
        await session.execute(
            delete(PushSubscription).where(
                PushSubscription.endpoint.in_(dead_endpoints)
            )
        )
        await session.commit()

    return {"sent": sent, "removed": len(dead_endpoints), "total": len(subs)}


def build_news_payload(title: str, count: int, lang: str = "az") -> dict:
    """Yeni xəbər bildirişinin məzmununu qurur (4 dil)."""
    headlines = {
        "az": ("NexusIQ — yeni xəbər", f"{count} yeni xəbər əlavə olundu"),
        "en": ("NexusIQ — new news", f"{count} new stories added"),
        "ru": ("NexusIQ — новости", f"Добавлено новостей: {count}"),
        "tr": ("NexusIQ — yeni haber", f"{count} yeni haber eklendi"),
    }
    head, body = headlines.get(lang, headlines["az"])
    return {
        "title": head,
        "body": title or body,
        "url": "/",
        "tag": "nexusiq-news",
    }


def build_anomaly_payload(label: str, change_pct: float, price_z: float) -> dict:
    """Ekstremal anomaliya bildirişinin məzmunu."""
    arrow = "▲" if change_pct >= 0 else "▼"
    return {
        "title": f"NexusIQ — anomaliya: {label}",
        "body": f"{arrow} {change_pct:+.2f}% (z={price_z:.1f}) qeyri-adi hərəkət",
        "url": "/anomalies",
        "tag": "nexusiq-anomaly",
    }
