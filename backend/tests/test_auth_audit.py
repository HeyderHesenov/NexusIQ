"""Auth audit log — hadisə yazılması, sahiblik (IDOR), retention.

Öz-session `record_audit` HTTP-yolundan test DB-yə yazır (conftest `client` fixture
`AsyncSessionLocal`-ı test factory-yə yönəldir). Uğursuz login `user_id=NULL` yazır
(forensika), uğurlu hadisələr user-ə bağlanır. `/me/audit` yalnız öz sətirlərini verir.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core import cookies
from app.models import AuthAuditLog, User
from app.services import audit, auth_service

PW = "testpassword123"
BASE = "/api/v1/auth"


def _csrf(client):
    return {"X-CSRF-Token": client.cookies.get(cookies.csrf_name())}


async def _register(client, email, pw=PW):
    return await client.post(f"{BASE}/register", json={"email": email, "password": pw})


async def _login(client, email, pw=PW):
    return await client.post(f"{BASE}/login", json={"email": email, "password": pw})


# ---- yazılma ----

async def test_login_success_writes_row_bound_to_user(client, db):
    await _register(client, "au1@example.com")
    await _login(client, "au1@example.com")
    u = await db.scalar(select(User).where(User.email == "au1@example.com"))
    row = await db.scalar(
        select(AuthAuditLog).where(AuthAuditLog.event == "login_success")
    )
    assert row is not None
    assert row.user_id == u.id


async def test_login_failure_writes_null_user(client, db):
    await _register(client, "au2@example.com")
    r = await _login(client, "au2@example.com", pw="wrong-password-123")
    assert r.status_code == 401
    row = await db.scalar(
        select(AuthAuditLog).where(AuthAuditLog.event == "login_failure")
    )
    assert row is not None
    assert row.user_id is None  # naməlum-cəhd forensikası, user feed-ində görünmür
    assert row.meta and row.meta.get("email") == "au2@example.com"


async def test_register_writes_row(client, db):
    await _register(client, "au3@example.com")
    u = await db.scalar(select(User).where(User.email == "au3@example.com"))
    row = await db.scalar(select(AuthAuditLog).where(AuthAuditLog.event == "register"))
    assert row is not None and row.user_id == u.id


async def test_session_revoke_writes_row(client, db):
    await _register(client, "au4@example.com")
    await _login(client, "au4@example.com")
    u = await db.scalar(select(User).where(User.email == "au4@example.com"))
    _, other = await auth_service.create_session(db, u)  # ikinci "cihaz"
    await db.commit()
    r = await client.delete(f"{BASE}/sessions/{other.id}", headers=_csrf(client))
    assert r.status_code == 200
    row = await db.scalar(
        select(AuthAuditLog).where(AuthAuditLog.event == "session_revoke")
    )
    assert row is not None and row.user_id == u.id
    assert row.meta and row.meta.get("sid") == str(other.id)


async def test_logout_all_writes_row(client, db):
    await _register(client, "au5@example.com")
    await _login(client, "au5@example.com")
    r = await client.post(f"{BASE}/logout-all", headers=_csrf(client))
    assert r.status_code == 200
    row = await db.scalar(
        select(AuthAuditLog).where(AuthAuditLog.event == "logout_all")
    )
    assert row is not None


# ---- /me/audit sahiblik (IDOR) ----

async def test_me_audit_returns_own_only(client, db):
    # B — başqa istifadəçi, unikal işarəli audit sətri (IP).
    b = await auth_service.create_user(db, "victim@example.com", password_hash="x")
    await db.commit()
    db.add(AuthAuditLog(user_id=b.id, event="login_success", ip="203.0.113.9"))
    await db.commit()

    # A — real client user.
    await _register(client, "viewer@example.com")
    await _login(client, "viewer@example.com")
    r = await client.get("/api/v1/me/audit")
    assert r.status_code == 200
    events = r.json()
    assert len(events) >= 1  # ən azı register + login_success
    # B-nin işarəli sətri A-ya sızmamalıdır.
    assert all(e.get("ip") != "203.0.113.9" for e in events)
    assert any(e["event"] == "login_success" for e in events)


# ---- retention ----

async def test_cleanup_audit_deletes_old(db):
    u = await auth_service.create_user(db, "ret@example.com", password_hash="x")
    await db.commit()
    old = AuthAuditLog(user_id=u.id, event="login_success")
    db.add(old)
    await db.flush()
    old.created_at = datetime.now(timezone.utc) - timedelta(days=120)
    db.add(AuthAuditLog(user_id=u.id, event="login_success"))  # təzə
    await db.commit()
    n = await audit.cleanup_audit(db, keep_days=90)
    assert n == 1
    assert (await db.scalar(select(func.count()).select_from(AuthAuditLog))) == 1
