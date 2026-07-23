"""Auth route-ları — register/login/refresh/logout/password/reset (real app + test DB).

Kök səbəb / niyə: bunlar auth-un ictimai səthidir. Enumerasiya-müqavimət, login kilidi,
Set-Cookie wire-formatı və reset tək-istifadəliyi burada pinlənir.
"""
from __future__ import annotations

import time

import pytest
from sqlalchemy import func, select

from app.core import cookies
from app.models import AuthSession, PasswordResetToken, User
from app.services import auth_service

PW = "testpassword123"
BASE = "/api/v1/auth"


def _csrf(client):
    return {"X-CSRF-Token": client.cookies.get(cookies.csrf_name())}


async def _register(client, email, pw=PW):
    return await client.post(f"{BASE}/register", json={"email": email, "password": pw})


async def _login(client, email, pw=PW):
    return await client.post(f"{BASE}/login", json={"email": email, "password": pw})


# ---- register ----

async def test_register_202(client):
    r = await _register(client, "a@example.com")
    assert r.status_code == 202
    assert r.json() == {"ok": True}


async def test_register_same_email_byte_identical(client):
    r1 = await _register(client, "dup@example.com")
    r2 = await _register(client, "dup@example.com")
    assert r1.status_code == r2.status_code == 202
    assert r1.content == r2.content  # enumerasiya yox


async def test_register_weak_password_422(client):
    r = await client.post(f"{BASE}/register", json={"email": "w@example.com", "password": "short"})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "password_too_short"


# ---- login + cookie wire format ----

async def test_login_sets_cookies_correctly(client):
    await _register(client, "c@example.com")
    r = await _login(client, "c@example.com")
    assert r.status_code == 200
    setc = " ".join(r.headers.get_list("set-cookie"))
    assert "nexusiq_at=" in setc and "nexusiq_rt=" in setc and "nexusiq_csrf=" in setc
    # access = Lax + HttpOnly + Max-Age=600
    assert "samesite=lax" in setc.lower()
    assert "httponly" in setc.lower()
    assert "max-age=600" in setc.lower()
    # refresh = Strict
    assert "samesite=strict" in setc.lower()
    # cookie_secure=False → __Host- prefiks YOX, Secure YOX
    assert "__host-" not in setc.lower()


async def test_wrong_password_and_unknown_email_identical_401(client):
    await _register(client, "real@example.com")
    r_wrong = await _login(client, "real@example.com", "wrongpassword123")
    r_unknown = await _login(client, "nobody@example.com", PW)
    assert r_wrong.status_code == r_unknown.status_code == 401
    assert r_wrong.json() == r_unknown.json()  # byte-identik → enumerasiya yox
    assert r_wrong.json()["detail"]["code"] == "invalid_credentials"


async def test_google_only_user_password_login_generic_401(client, db):
    # Parolsuz (Google-only) istifadəçi → login "parol yoxdur" sızmasın, generik 401.
    await auth_service.create_user(db, "g@example.com", password_hash=None, email_verified=True)
    await db.commit()
    r = await _login(client, "g@example.com", "anypassword12345")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "invalid_credentials"


# ---- lockout ----

async def test_lockout_after_5_failures(client):
    await _register(client, "lock@example.com")
    for _ in range(5):
        r = await _login(client, "lock@example.com", "wrongpassword123")
        assert r.status_code == 401
    # 6-cı → kilidli
    r = await _login(client, "lock@example.com", "wrongpassword123")
    assert r.status_code == 429
    assert "retry-after" in {k.lower() for k in r.headers}
    assert r.json()["detail"]["code"] == "too_many_attempts"
    # düzgün parol da kilid müddətində fail (429)
    r = await _login(client, "lock@example.com", PW)
    assert r.status_code == 429


async def test_success_resets_counter(client):
    await _register(client, "reset-count@example.com")
    for _ in range(4):  # 4 < 5 → kilid yoxdur
        await _login(client, "reset-count@example.com", "wrongpassword123")
    r = await _login(client, "reset-count@example.com", PW)  # düzgün → uğur, sayğac sıfır
    assert r.status_code == 200


# ---- me ----

async def test_me_unauthenticated(client):
    r = await client.get(f"{BASE}/me")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "unauthenticated"


async def test_me_token_expired(client, monkeypatch):
    import uuid

    from app.core import cookies, jwtsvc
    from app.core.config import settings

    # Vaxtı bitmiş token DÜZƏLT + cookie-ni ƏL İLƏ qoy (access_ttl-i mənfi etsək cookie
    # max-age də mənfi olub saxlanmazdı). decode expiry-ni user axtarışından əvvəl tutur.
    monkeypatch.setattr(settings, "access_ttl_seconds", -5)
    token = jwtsvc.mint_access(str(uuid.uuid4()), "sid-x", tv=0)
    monkeypatch.setattr(settings, "access_ttl_seconds", 600)
    client.cookies.set(cookies.access_name(), token)
    r = await client.get(f"{BASE}/me")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "token_expired"  # frontend refresh məhz buna baxır


async def test_me_authenticated(client):
    await _register(client, "meok@example.com")
    await _login(client, "meok@example.com")
    r = await client.get(f"{BASE}/me")
    assert r.status_code == 200
    assert r.json()["email"] == "meok@example.com"


# ---- refresh ----

async def test_refresh_rotates_and_returns_user(client):
    await _register(client, "ref@example.com")
    await _login(client, "ref@example.com")
    r = await client.post(f"{BASE}/refresh", headers=_csrf(client))
    assert r.status_code == 200
    assert r.json()["email"] == "ref@example.com"


async def test_refresh_no_cookie_401(client):
    r = await client.post(f"{BASE}/refresh")
    assert r.status_code == 401


# ---- logout ----

async def test_logout_clears_and_revokes(client, db):
    await _register(client, "lo@example.com")
    await _login(client, "lo@example.com")
    r = await client.post(f"{BASE}/logout", headers=_csrf(client))
    assert r.status_code == 200
    setc = " ".join(r.headers.get_list("set-cookie")).lower()
    assert "max-age=0" in setc  # cookie silindi
    u = await db.scalar(select(User).where(User.email == "lo@example.com"))
    revoked = await db.scalar(
        select(func.count()).select_from(AuthSession).where(
            AuthSession.user_id == u.id, AuthSession.revoked_at.isnot(None)
        )
    )
    assert revoked == 1


# ---- password change ----

async def test_password_change_revokes_others_keeps_current(client, db):
    await _register(client, "pw@example.com")
    await _login(client, "pw@example.com")  # sessiya A (client cookie-lərində)
    u = await db.scalar(select(User).where(User.email == "pw@example.com"))
    # ikinci sessiya B (birbaşa)
    _, sess_b = await auth_service.create_session(db, u)
    await db.commit()

    r = await client.post(
        f"{BASE}/password",
        headers=_csrf(client),
        json={"currentPassword": PW, "newPassword": "brandnewpass123"},
    )
    assert r.status_code == 200
    # B revoked, A (cari) sağ
    await db.refresh(sess_b)
    assert sess_b.revoked_at is not None and sess_b.revoked_reason == "password_change"


# ---- reset ----

async def test_reset_request_enumeration_safe_and_timed(client, db):
    await _register(client, "known@example.com")

    t0 = time.monotonic()
    r_known = await client.post(f"{BASE}/password-reset/request", json={"email": "known@example.com"})
    known_elapsed = time.monotonic() - t0

    t0 = time.monotonic()
    r_unknown = await client.post(f"{BASE}/password-reset/request", json={"email": "ghost@example.com"})
    unknown_elapsed = time.monotonic() - t0

    assert r_known.status_code == r_unknown.status_code == 202
    assert r_known.content == r_unknown.content
    assert known_elapsed >= 0.24 and unknown_elapsed >= 0.24  # 250ms floor
    # token yalnız məlum üçün yaradıldı
    n = await db.scalar(select(func.count()).select_from(PasswordResetToken))
    assert n == 1


async def test_reset_confirm_single_use_and_revokes(client, db):
    # Reset istifadəçisi login OLMUR (email linkindən gəlir) → stale cookie yox, CSRF Qat 2 atlanır.
    await _register(client, "rc@example.com")
    u = await db.scalar(select(User).where(User.email == "rc@example.com"))
    _, sess = await auth_service.create_session(db, u)  # canlı sessiya (reset ləğv etməli)
    raw = await auth_service.create_reset_token(db, u)
    await db.commit()

    r = await client.post(f"{BASE}/password-reset/confirm", json={"token": raw, "password": "freshpass123456"})
    assert r.status_code == 200
    assert "set-cookie" not in {k.lower() for k in r.headers}  # auto-login YOX
    await db.refresh(sess)
    assert sess.revoked_at is not None and sess.revoked_reason == "reset"
    # təkrar istifadə → 400
    r2 = await client.post(f"{BASE}/password-reset/confirm", json={"token": raw, "password": "another123456"})
    assert r2.status_code == 400
    # köhnə parolla login artıq işləməməli, yenisi işləməli
    assert (await _login(client, "rc@example.com", PW)).status_code == 401
    assert (await _login(client, "rc@example.com", "freshpass123456")).status_code == 200


# ---- rate limit (parol endpoint-ləri — əvvəl throttle-suz idi) ----

async def test_password_change_rate_limited(client):
    await _register(client, "pwrl@example.com")
    await _login(client, "pwrl@example.com")
    # Yanlış cari parol → 401 (validate/hibp-dən əvvəl, şəbəkə çağırışı yox). Limit 10/60s.
    for _ in range(10):
        r = await client.post(
            f"{BASE}/password",
            headers=_csrf(client),
            json={"currentPassword": "wrong-current-1", "newPassword": "brandnewpass123"},
        )
        assert r.status_code == 401
    r = await client.post(
        f"{BASE}/password",
        headers=_csrf(client),
        json={"currentPassword": "wrong-current-1", "newPassword": "brandnewpass123"},
    )
    assert r.status_code == 429
    assert "retry-after" in {k.lower() for k in r.headers}


async def test_reset_confirm_rate_limited(client):
    # Zəif parol → 422 (validate_password, hibp-dən ƏVVƏL → şəbəkə yox). Limit 10/3600s.
    for _ in range(10):
        r = await client.post(
            f"{BASE}/password-reset/confirm", json={"token": "x", "password": "short"}
        )
        assert r.status_code == 422
    r = await client.post(
        f"{BASE}/password-reset/confirm", json={"token": "x", "password": "short"}
    )
    assert r.status_code == 429
