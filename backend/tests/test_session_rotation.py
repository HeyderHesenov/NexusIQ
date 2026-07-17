"""Refresh rotasiya + reuse detection — flaqman test (real Postgres + FOR UPDATE).

Kök səbəb: rotasiyanın prod-da geri qaytarılmasının ƏN çox səbəbi iki-tab-ın yanlış
reuse alarmıdır. Grace window bunu bağlayır. Bu testlər grace-i, oğurluq aşkarını və
konkurent rotasiyanın (FOR UPDATE) tək qalibini pinləyir.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models import AuthSession, User
from app.services import auth_service


def _now():
    return datetime.now(timezone.utc)


async def _mk_user(db, email="u@example.com"):
    u = User(email=email, password_hash=None)
    db.add(u)
    await db.flush()
    return u


async def test_rotate_issues_new_and_old_dies_after_grace(db, monkeypatch):
    monkeypatch.setattr(settings, "rotation_grace_seconds", 0)
    u = await _mk_user(db)
    raw, _ = await auth_service.create_session(db, u)
    await db.commit()

    new_raw, _ = await auth_service.rotate_refresh(db, raw)
    await db.commit()
    assert new_raw is not None and new_raw != raw

    # köhnə token (indi previous), grace=0 → oğurluq → ReuseDetected
    with pytest.raises(auth_service.ReuseDetected):
        await auth_service.rotate_refresh(db, raw)


async def test_reuse_within_grace_is_benign(db):
    # grace defolt (10s) — köhnə token dərhal təqdim = benign iki-tab race.
    u = await _mk_user(db)
    raw, _ = await auth_service.create_session(db, u)
    await db.commit()
    new_raw, _ = await auth_service.rotate_refresh(db, raw)
    await db.commit()

    result_raw, sess = await auth_service.rotate_refresh(db, raw)
    assert result_raw is None          # rotasiya OLMADI
    assert sess.revoked_at is None     # alarm YOX


async def test_reuse_after_grace_revokes_all(db, session_factory, monkeypatch):
    monkeypatch.setattr(settings, "rotation_grace_seconds", 0)
    u = await _mk_user(db)
    raw, _ = await auth_service.create_session(db, u)
    await auth_service.create_session(db, u)  # ikinci sessiya
    await db.commit()

    await auth_service.rotate_refresh(db, raw)
    await db.commit()
    with pytest.raises(auth_service.ReuseDetected):
        await auth_service.rotate_refresh(db, raw)

    # Təsdiq: TƏMİZ sessiyada bütün sessiyalar revoked (bulk UPDATE identity-map-i keçir).
    async with session_factory() as s2:
        rows = (await s2.execute(select(AuthSession).where(AuthSession.user_id == u.id))).scalars().all()
        assert len(rows) == 2
        assert all(r.revoked_at is not None and r.revoked_reason == "reuse" for r in rows)


async def test_reuse_of_revoked_session(db):
    u = await _mk_user(db)
    raw, s = await auth_service.create_session(db, u)
    await db.commit()
    await auth_service.revoke_session(db, s.id, "logout")
    await db.commit()
    with pytest.raises(auth_service.ReuseDetected):
        await auth_service.rotate_refresh(db, raw)


async def test_absolute_expiry(db):
    u = await _mk_user(db)
    raw, s = await auth_service.create_session(db, u)
    s.expires_at = _now() - timedelta(seconds=1)
    await db.commit()
    with pytest.raises(auth_service.InvalidRefresh):
        await auth_service.rotate_refresh(db, raw)


async def test_idle_expiry(db):
    u = await _mk_user(db)
    raw, s = await auth_service.create_session(db, u)
    s.last_used_at = _now() - timedelta(days=settings.refresh_idle_days + 1)
    await db.commit()
    with pytest.raises(auth_service.InvalidRefresh):
        await auth_service.rotate_refresh(db, raw)


async def test_unknown_token_invalid(db):
    with pytest.raises(auth_service.InvalidRefresh):
        await auth_service.rotate_refresh(db, "totally-unknown-token")


async def test_concurrent_rotation_exactly_one_wins(db, session_factory):
    # İki konkurent rotasiya (eyni cari token) → FOR UPDATE serialize edir →
    # tam biri rotasiya, digəri benign grace; HEÇ BİRİ reuse alarmı yox.
    u = await _mk_user(db)
    raw, _ = await auth_service.create_session(db, u)
    await db.commit()

    async def _rot():
        async with session_factory() as s:
            try:
                new_raw, _ = await auth_service.rotate_refresh(s, raw)
                await s.commit()
                return ("ok", new_raw)
            except auth_service.ReuseDetected:
                return ("reuse", None)
            except auth_service.InvalidRefresh:
                return ("invalid", None)

    results = await asyncio.gather(_rot(), _rot())
    kinds = [k for k, _ in results]
    assert "reuse" not in kinds, f"yanlış reuse alarmı: {results}"
    oks = [v for k, v in results if k == "ok"]
    assert sum(1 for v in oks if v is not None) == 1   # tam biri rotasiya
    assert sum(1 for v in oks if v is None) == 1        # digəri benign
