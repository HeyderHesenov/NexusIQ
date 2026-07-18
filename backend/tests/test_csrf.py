"""CSRF middleware — Origin qatı + HMAC double-submit (sid-bağlı).

Kök səbəb: CT-əsaslı CSRF müdafiəsinin boş-`type` Blob bypass-ı var. Bu testlər
Origin qatını, sessiya olanda double-submit-i, sid-bağlamanı və CT-siz bypass-ı pinləyir.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import cookies, csrf, jwtsvc
from app.core.config import settings

_ORIGIN = "http://localhost:3000"


@pytest.fixture(autouse=True)
def _cfg(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "test-secret-long-enough-32chars-min-000000")
    monkeypatch.setattr(settings, "csrf_secret", "test-csrf-secret-long-enough-000000")
    monkeypatch.setattr(settings, "cookie_secure", False)
    monkeypatch.setattr(settings, "backend_cors_origins", _ORIGIN)


@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(csrf.CsrfMiddleware)

    @app.get("/x")
    async def _get():
        return {"ok": True}

    @app.post("/x")
    async def _post():
        return {"ok": True}

    return TestClient(app)


def _session_cookies(sid="sess-123", tv=0):
    access = jwtsvc.mint_access("user-1", sid, tv=tv)
    csrf_val = csrf.make_csrf_token(sid)
    return {cookies.access_name(): access, cookies.csrf_name(): csrf_val}, csrf_val


def test_get_always_passes(client):
    assert client.get("/x").status_code == 200  # Origin-siz belə


def test_post_no_origin_denied(client):
    r = client.post("/x")
    assert r.status_code == 403
    assert r.json()["code"] == "csrf_origin_mismatch"


def test_post_bad_origin_denied(client):
    r = client.post("/x", headers={"Origin": "http://evil.example.com"})
    assert r.status_code == 403


def test_post_good_origin_no_session_passes(client):
    # Sessiya yoxdur → Qat 2 atlanır → keçir.
    r = client.post("/x", headers={"Origin": _ORIGIN})
    assert r.status_code == 200


def test_post_session_no_csrf_header_denied(client):
    ck, _ = _session_cookies()
    r = client.post("/x", headers={"Origin": _ORIGIN}, cookies=ck)
    assert r.status_code == 403
    assert r.json()["code"] == "csrf_token_missing"


def test_post_session_header_neq_cookie_denied(client):
    ck, _ = _session_cookies()
    r = client.post("/x", headers={"Origin": _ORIGIN, "X-CSRF-Token": "wrong"}, cookies=ck)
    assert r.status_code == 403


def test_post_session_valid_csrf_passes(client):
    ck, csrf_val = _session_cookies()
    r = client.post("/x", headers={"Origin": _ORIGIN, "X-CSRF-Token": csrf_val}, cookies=ck)
    assert r.status_code == 200


def test_post_csrf_bound_to_different_sid_denied(client):
    # access token sid='sess-123', amma csrf token 'other-sid'-ə bağlı → sid bağlaması fail.
    access = jwtsvc.mint_access("user-1", "sess-123", tv=0)
    csrf_val = csrf.make_csrf_token("other-sid")
    ck = {cookies.access_name(): access, cookies.csrf_name(): csrf_val}
    r = client.post("/x", headers={"Origin": _ORIGIN, "X-CSRF-Token": csrf_val}, cookies=ck)
    assert r.status_code == 403
    assert r.json()["code"] == "csrf_token_invalid"


def test_ct_bypass_denied(client):
    # §4 bypass: CT-siz JSON gövdə, Origin-siz → Origin qatı 403 verir.
    r = client.post("/x", content=b'{"key":"btc"}')  # heç bir Content-Type / Origin
    assert r.status_code == 403
