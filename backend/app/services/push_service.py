"""Web Push xidməti — abunə saxla/sil + bildiriş göndər (pywebpush)."""
from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor

from pywebpush import WebPushException, webpush
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import PushSubscription

logger = logging.getLogger("nexusiq.push")

# Endpoint cavabı bu kodlarla gəlsə abunə ölüdür — bazadan silinir.
_DEAD_STATUS = {404, 410}

# HTTP timeout-u AÇIQ verilməlidir. pywebpush-un `webpush(timeout=None)` defoltu
# `send()`-ə AÇIQ ötürülür, `send()` isə `kwargs.pop("timeout", 10000)` edir —
# açar MÖVCUD olduğu üçün pop 10000 fallback-ına HEÇ VAXT çatmır, `None` qaytarır
# və `requests.post(timeout=None)` ƏBƏDİ bloklanır (pywebpush 2.3.0-da yoxlanıldı).
_SEND_TIMEOUT = 10.0

# AYRICA hovuz + semafor — `asyncio.to_thread` DEFOLT hovuzu işlədir (8 CPU-da
# cəmi 12 işçi), onu isə yfinance çağırışları doldurur (bax img_cache.py:58).
# Limitsiz fan-out + timeout-suz webpush = cavab verməyən 12 endpoint bütün
# defolt hovuzu əbədi tutur → market/assets/correlation/radar/netguard DNS —
# hamısı növbəyə düşür, `max_instances=1` ingest-i həmişəlik dayandırır.
# Ayrıca hovuz o zənciri defolt hovuzdan tamamilə ayırır; semafor isə bir
# göndərmə dalğasının hovuzu doldurmasının qarşısını alır.
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="webpush")
_SEND_SEM = asyncio.Semaphore(8)


_USER_CAP = 10  # istifadəçi başına abunə tavanı (köhnəni bud)


async def _prune_user(session: AsyncSession, user_id) -> None:
    subs = (
        await session.scalars(
            select(PushSubscription)
            .where(PushSubscription.user_id == user_id)
            .order_by(PushSubscription.created_at.desc())
        )
    ).all()
    for old in subs[_USER_CAP:]:
        await session.delete(old)


async def save_subscription(
    session: AsyncSession, *, user_id, endpoint: str, p256dh: str, auth: str, lang: str = "az"
) -> PushSubscription:
    """Abunəni yaradır/yeniləyir (endpoint upsert). Sahib cari istifadəçiyə TƏYİN olunur —
    brauzer kim login-dirsə ona aiddir."""
    existing = await session.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )
    if existing is not None:
        existing.user_id = user_id  # reassignment: brauzer indi kim login-dirsə onundur
        existing.p256dh = p256dh
        existing.auth = auth
        existing.lang = lang
        sub = existing
    else:
        sub = PushSubscription(
            user_id=user_id, endpoint=endpoint, p256dh=p256dh, auth=auth, lang=lang
        )
        session.add(sub)
    await session.flush()
    await _prune_user(session, user_id)
    await session.commit()
    return sub


async def delete_subscription(session: AsyncSession, endpoint: str, user_id) -> None:
    """Abunəni endpoint + SAHİB üzrə silir (idempotent). Sahiblik yoxlaması — endpoint
    entropiyasına güvənmə."""
    await session.execute(
        delete(PushSubscription).where(
            PushSubscription.endpoint == endpoint,
            PushSubscription.user_id == user_id,
        )
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
            timeout=_SEND_TIMEOUT,
        )
        return None
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in _DEAD_STATUS:
            return status
        logger.warning("Push göndərmə xətası: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 — timeout/şəbəkə: bir abunə hamısını batırmasın
        logger.warning("Push göndərmə xətası (şəbəkə): %s", exc)
        return None


async def _send_one(sub: PushSubscription, payload: dict) -> int | None:
    """Semafor + ayrıca hovuz altında tək abunəyə göndərir."""
    loop = asyncio.get_running_loop()
    async with _SEND_SEM:
        return await loop.run_in_executor(_POOL, _send_raw, sub, payload)


async def _send_to_subs(
    session: AsyncSession, subs: list[PushSubscription], payload: dict
) -> dict[str, int]:
    """Verilmiş abunə siyahısına paralel göndərir + ölüləri təmizləyir."""
    # Sinxron webpush çağırışlarını paralel thread-lərdə işlət — event loop
    # bloklanmasın. Paralellik semafor + ayrıca hovuzla məhdudlaşır (bax `_POOL`).
    statuses = await asyncio.gather(*(_send_one(sub, payload) for sub in subs))
    sent = 0
    dead_endpoints: list[str] = []
    for sub, status in zip(subs, statuses):
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


async def send_to_all(session: AsyncSession, payload: dict) -> dict[str, int]:
    """BÜTÜN abunələrə (ingest broadcast) — yeni xəbər hamıya. Ölüləri təmizləyir."""
    if not settings.push_enabled:
        logger.info("Push deaktiv (VAPID açarları yoxdur) — atlanır.")
        return {"sent": 0, "removed": 0, "total": 0}
    subs = (await session.scalars(select(PushSubscription))).all()
    return await _send_to_subs(session, subs, payload)


async def send_to_user(session: AsyncSession, user_id, payload: dict) -> dict[str, int]:
    """YALNIZ bir istifadəçinin abunələrinə (məs. /push/test — hamıya spam yox)."""
    if not settings.push_enabled:
        return {"sent": 0, "removed": 0, "total": 0}
    subs = (
        await session.scalars(
            select(PushSubscription).where(PushSubscription.user_id == user_id)
        )
    ).all()
    return await _send_to_subs(session, subs, payload)


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
