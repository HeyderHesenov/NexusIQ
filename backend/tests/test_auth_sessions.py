"""Sessiya idarəsi ("cihazların") + təmizlik job-ları (Addım 14 hardening)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core import budget
from app.models import AiUsage, AuthSession, User
from app.services import auth_service

AUTH = "/api/v1/auth"
PW = "testpassword123"


def _csrf(client):
    from app.core import cookies

    return {"X-CSRF-Token": client.cookies.get(cookies.csrf_name())}


async def _mk_user(db, email="sess@example.com"):
    u = await auth_service.create_user(db, email, password_hash="x")
    await db.commit()
    return u


async def test_list_active_excludes_revoked(db):
    u = await _mk_user(db)
    _, s1 = await auth_service.create_session(db, u)
    _, s2 = await auth_service.create_session(db, u)
    await db.commit()
    await auth_service.revoke_session(db, s2.id, "logout")
    await db.commit()
    active = await auth_service.list_active_sessions(db, u.id)
    assert {str(s.id) for s in active} == {str(s1.id)}


async def test_cleanup_sessions_deletes_old(db):
    u = await _mk_user(db)
    _, old = await auth_service.create_session(db, u)
    old.expires_at = datetime.now(timezone.utc) - timedelta(days=10)  # çoxdan bitib
    _, fresh = await auth_service.create_session(db, u)
    await db.commit()
    n = await auth_service.cleanup_sessions(db, keep_days=7)
    assert n == 1
    remaining = await db.scalar(select(func.count()).select_from(AuthSession))
    assert remaining == 1


async def test_cleanup_ai_usage_deletes_old(db):
    u = await _mk_user(db)
    await budget.record_usage(db, "chat", 1, user_id=u.id)
    await db.flush()
    old = await db.scalar(select(AiUsage))
    old.created_at = datetime.now(timezone.utc) - timedelta(days=120)
    await budget.record_usage(db, "chat", 1, user_id=u.id)  # təzə
    await db.commit()
    n = await budget.cleanup_usage(db, keep_days=90)
    assert n == 1
    assert (await db.scalar(select(func.count()).select_from(AiUsage))) == 1


# ---- endpoint-lər ----

async def test_sessions_endpoint_lists_and_marks_current(client):
    await client.post(f"{AUTH}/register", json={"email": "se@example.com", "password": PW})
    await client.post(f"{AUTH}/login", json={"email": "se@example.com", "password": PW})
    r = await client.get(f"{AUTH}/sessions")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) >= 1
    assert any(s["current"] for s in rows)  # cari sessiya işarələnir


async def test_revoke_other_session_and_idor(client, db):
    await client.post(f"{AUTH}/register", json={"email": "sr@example.com", "password": PW})
    await client.post(f"{AUTH}/login", json={"email": "sr@example.com", "password": PW})
    u = await db.scalar(select(User).where(User.email == "sr@example.com"))
    _, other = await auth_service.create_session(db, u)  # ikinci cihaz
    await db.commit()
    # öz başqa sessiyanı ləğv et → 200
    r = await client.delete(f"{AUTH}/sessions/{other.id}", headers=_csrf(client))
    assert r.status_code == 200
    # başqasının / mövcud olmayan sessiya → 404 (IDOR yox)
    import uuid

    r2 = await client.delete(f"{AUTH}/sessions/{uuid.uuid4()}", headers=_csrf(client))
    assert r2.status_code == 404
