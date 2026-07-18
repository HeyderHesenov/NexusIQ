"""Google ID-token yoxlaması — lokal RS256 keypair + monkeypatched JWKS.

Kök səbəb: bugünkü kod ID-token-i heç yoxlamır (browser-side userinfo). Bu testlər
`aud`/`iss`/imza/exp/email_verified/nonce yoxlamalarını və sub-üzrə bağlamanı pinləyir.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt as pyjwt
import pytest
from sqlalchemy import func, select

from app.core import cookies
from app.core.config import settings
from app.models import User
from app.services import google_auth

BASE = "/api/v1/auth"
CLIENT_ID = "test-client-id.apps.googleusercontent.com"


@pytest.fixture
def gkey(monkeypatch):
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        google_auth, "_get_signing_key",
        lambda cred: SimpleNamespace(key=key.public_key()),
    )
    monkeypatch.setattr(settings, "google_client_id", CLIENT_ID)
    return key


def _id_token(key, nonce, *, aud=CLIENT_ID, iss="https://accounts.google.com",
              sub="google-sub-1", email="user@gmail.com", email_verified=True,
              exp_delta=3600, name="Test User", picture=None):
    now = datetime.now(timezone.utc)
    payload = {
        "iss": iss, "aud": aud, "sub": sub, "email": email,
        "email_verified": email_verified, "iat": now,
        "exp": now + timedelta(seconds=exp_delta), "nonce": nonce, "name": name,
    }
    if picture:
        payload["picture"] = picture
    return pyjwt.encode(payload, key, algorithm="RS256")


async def _nonce(client):
    r = await client.get(f"{BASE}/google/nonce")
    return r.json()["nonce"]


def _csrf(client):
    return {"X-CSRF-Token": client.cookies.get(cookies.csrf_name())}


async def test_valid_creates_user(client, db, gkey):
    n = await _nonce(client)
    r = await client.post(f"{BASE}/google", json={"credential": _id_token(gkey, n)})
    assert r.status_code == 200
    assert r.json()["email"] == "user@gmail.com"
    u = await db.scalar(select(User).where(User.email == "user@gmail.com"))
    assert u is not None and u.password_hash is None and u.email_verified_at is not None


async def test_wrong_aud_rejected(client, gkey):
    n = await _nonce(client)
    r = await client.post(f"{BASE}/google", json={"credential": _id_token(gkey, n, aud="someone-else")})
    assert r.status_code == 401 and r.json()["detail"]["code"] == "google_invalid"


async def test_wrong_iss_rejected(client, gkey):
    n = await _nonce(client)
    r = await client.post(f"{BASE}/google", json={"credential": _id_token(gkey, n, iss="evil")})
    assert r.status_code == 401


async def test_expired_rejected(client, gkey):
    n = await _nonce(client)
    r = await client.post(f"{BASE}/google", json={"credential": _id_token(gkey, n, exp_delta=-120)})
    assert r.status_code == 401


async def test_bad_signature_rejected(client, gkey):
    from cryptography.hazmat.primitives.asymmetric import rsa

    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    n = await _nonce(client)
    # başqa açarla imzalanıb, amma _get_signing_key əsl publik açarı qaytarır → imza fail
    r = await client.post(f"{BASE}/google", json={"credential": _id_token(other, n)})
    assert r.status_code == 401


async def test_email_unverified_rejected(client, gkey):
    n = await _nonce(client)
    r = await client.post(f"{BASE}/google", json={"credential": _id_token(gkey, n, email_verified=False)})
    assert r.status_code == 401


async def test_nonce_mismatch_rejected(client, gkey):
    await _nonce(client)  # cookie qoyulur
    r = await client.post(f"{BASE}/google", json={"credential": _id_token(gkey, "wrong-nonce")})
    assert r.status_code == 401


async def test_nonce_replay_rejected(client, gkey):
    n = await _nonce(client)
    tok = _id_token(gkey, n)
    r1 = await client.post(f"{BASE}/google", json={"credential": tok})
    assert r1.status_code == 200  # gnonce cookie silinir
    # təkrar (artıq authenticated → csrf lazım) → nonce cookie yoxdur → 401
    r2 = await client.post(f"{BASE}/google", json={"credential": tok}, headers=_csrf(client))
    assert r2.status_code == 401


async def test_no_client_id_503(client, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    r = await client.post(f"{BASE}/google", json={"credential": "x.y.z"})
    assert r.status_code == 503 and r.json()["detail"]["code"] == "google_not_configured"


async def test_links_existing_verified_email(client, db, gkey):
    from app.services import auth_service

    await auth_service.create_user(db, "linkme@gmail.com", password_hash="x", email_verified=True)
    await db.commit()
    n = await _nonce(client)
    r = await client.post(f"{BASE}/google", json={"credential": _id_token(gkey, n, email="linkme@gmail.com")})
    assert r.status_code == 200
    # yeni user yaradılmadı — mövcuda link olundu
    cnt = await db.scalar(select(func.count()).select_from(User).where(User.email == "linkme@gmail.com"))
    assert cnt == 1


async def test_same_sub_different_email_same_user_no_rewrite(client, db, gkey):
    n1 = await _nonce(client)
    r1 = await client.post(f"{BASE}/google", json={"credential": _id_token(gkey, n1, sub="S", email="first@gmail.com")})
    assert r1.status_code == 200
    n2 = await _nonce(client)
    r2 = await client.post(
        f"{BASE}/google",
        json={"credential": _id_token(gkey, n2, sub="S", email="second@gmail.com")},
        headers=_csrf(client),
    )
    assert r2.status_code == 200
    assert r2.json()["email"] == "first@gmail.com"  # email YENİDƏN YAZILMADI
    cnt = await db.scalar(select(func.count()).select_from(User))
    assert cnt == 1  # eyni user
