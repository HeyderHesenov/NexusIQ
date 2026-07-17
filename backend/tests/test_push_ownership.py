"""push_subscriptions sahiblik — B A-nın abunəsini silə bilməz; /test yalnız çağırana; cap 10.

Kök səbəb: köhnə kod endpoint-only idi (yalnız endpoint entropiyası ilə qorunurdu) və
/push/test send_to_all edirdi (paylaşılan DB-də bir nəfərin test düyməsi hamıya spam).
"""
from __future__ import annotations

from sqlalchemy import func, select

from app.models import PushSubscription, User
from app.services import auth_service, push_service


async def _mk_user(db, email):
    return await auth_service.create_user(db, email, password_hash="x")


async def _sub(db, user, endpoint):
    return await push_service.save_subscription(
        db, user_id=user.id, endpoint=endpoint, p256dh="p", auth="a"
    )


async def test_subscribe_binds_user(db):
    u = await _mk_user(db, "pa@example.com")
    await db.commit()
    sub = await _sub(db, u, "https://push.example/aaa")
    assert sub.user_id == u.id


async def test_b_cannot_unsubscribe_a(db):
    a = await _mk_user(db, "a@example.com")
    b = await _mk_user(db, "b@example.com")
    await db.commit()
    await _sub(db, a, "https://push.example/a-endpoint")
    # B A-nın endpoint-ini silməyə çalışır → heç nə silinmir (sahiblik yoxlaması)
    await push_service.delete_subscription(db, "https://push.example/a-endpoint", b.id)
    remaining = await db.scalar(
        select(func.count()).select_from(PushSubscription).where(
            PushSubscription.endpoint == "https://push.example/a-endpoint"
        )
    )
    assert remaining == 1  # A-nınkı toxunulmadı
    # A özü silə bilər
    await push_service.delete_subscription(db, "https://push.example/a-endpoint", a.id)
    gone = await db.scalar(
        select(func.count()).select_from(PushSubscription).where(
            PushSubscription.endpoint == "https://push.example/a-endpoint"
        )
    )
    assert gone == 0


async def test_cap_prunes_oldest(db):
    u = await _mk_user(db, "cap@example.com")
    await db.commit()
    for i in range(12):
        await _sub(db, u, f"https://push.example/cap-{i}")
    count = await db.scalar(
        select(func.count()).select_from(PushSubscription).where(
            PushSubscription.user_id == u.id
        )
    )
    assert count == 10  # cap 10, köhnə 2 budandı


async def test_send_to_user_scoped(db, monkeypatch):
    a = await _mk_user(db, "sa@example.com")
    b = await _mk_user(db, "sb@example.com")
    await db.commit()
    await _sub(db, a, "https://push.example/a1")
    await _sub(db, a, "https://push.example/a2")
    await _sub(db, b, "https://push.example/b1")

    # Push-u aktiv et + real göndərməni no-op et (VAPID yoxdur).
    monkeypatch.setattr(push_service.settings, "vapid_private_key", "x")
    monkeypatch.setattr(push_service.settings, "vapid_public_key", "y")

    async def _fake_send_one(sub, payload):
        return None  # canlı deyil, uğurlu say

    monkeypatch.setattr(push_service, "_send_one", _fake_send_one)

    stats = await push_service.send_to_user(db, a.id, {"title": "t", "body": "b"})
    assert stats["total"] == 2  # yalnız A-nın 2 abunəsi (B-yə YOX)
