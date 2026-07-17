"""Rate limiter — store abstraksiyası + per-scope açar ayrımı.

Kök səbəb / məqsəd: (1) `hit()` async olmalıdır ki, Redis sonra call site-ları
sync→async məcbur etməsin; (2) per-user və per-IP scope-lar ayrı büdcə almalıdır;
(3) store backend switch import vaxtı seçilir və naməlum backend fail-fast olur.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.core import ratelimit
from app.core.config import settings


def _run(coro):
    return asyncio.run(coro)


class _Client:
    def __init__(self, host: str) -> None:
        self.host = host


def _req(peer="1.1.1.1", user_id=None):
    st = SimpleNamespace()
    if user_id is not None:
        st.user_id = user_id
    return SimpleNamespace(headers={}, client=_Client(peer), state=st)


# ---- InMemoryStore semantikası ----

def test_store_allows_then_blocks_with_retry():
    store = ratelimit.InMemoryStore()
    allowed1, _ = _run(store.hit("k", 2, 60.0))
    allowed2, _ = _run(store.hit("k", 2, 60.0))
    allowed3, retry = _run(store.hit("k", 2, 60.0))
    assert allowed1 and allowed2
    assert allowed3 is False
    assert retry >= 1


def test_store_window_expiry_allows_again():
    store = ratelimit.InMemoryStore()
    assert _run(store.hit("k", 1, 0.2))[0] is True
    assert _run(store.hit("k", 1, 0.2))[0] is False
    _run(asyncio.sleep(0.25))
    assert _run(store.hit("k", 1, 0.2))[0] is True  # pəncərə keçdi


def test_distinct_keys_have_separate_budgets():
    store = ratelimit.InMemoryStore()
    assert _run(store.hit("a", 1, 60.0))[0] is True
    assert _run(store.hit("b", 1, 60.0))[0] is True  # ayrı açar → ayrı büdcə
    assert _run(store.hit("a", 1, 60.0))[0] is False


# ---- scope açarı: per-user vs per-IP ----

def test_two_users_one_ip_get_separate_budgets():
    # Eyni IP, iki fərqli user → user scope-da ayrı açar.
    kA = ratelimit._scope_key(_req(peer="1.1.1.1", user_id="A"), "user")
    kB = ratelimit._scope_key(_req(peer="1.1.1.1", user_id="B"), "user")
    assert kA != kB
    assert kA == "u:A" and kB == "u:B"


def test_one_user_two_ips_shares_budget():
    kA = ratelimit._scope_key(_req(peer="1.1.1.1", user_id="A"), "user")
    kB = ratelimit._scope_key(_req(peer="2.2.2.2", user_id="A"), "user")
    assert kA == kB == "u:A"  # user scope IP-ə baxmır


def test_user_scope_without_auth_falls_back_to_ip(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
    k = ratelimit._scope_key(_req(peer="1.1.1.1", user_id=None), "user")
    assert k == "ip:1.1.1.1"  # heç vaxt boş açar


# ---- dependency 429 davranışı ----

def test_dependency_raises_429_after_limit():
    from fastapi import HTTPException

    dep = ratelimit.rate_limit("t_dep", 1, 60.0)
    _run(dep(_req(peer="7.7.7.7")))  # 1-ci OK
    try:
        _run(dep(_req(peer="7.7.7.7")))
        raise AssertionError("429 gözlənilirdi")
    except HTTPException as e:
        assert e.status_code == 429
        assert "Retry-After" in e.headers


# ---- backend switch ----

def test_unknown_backend_fails_fast(monkeypatch):
    monkeypatch.setattr(settings, "ratelimit_backend", "redis")
    try:
        ratelimit._make_store()
        raise AssertionError("naməlum backend RuntimeError verməli idi")
    except RuntimeError as e:
        assert "redis" in str(e)


# ---- real FastAPI Request üzərindən inteqrasiya (stub-ları reallıqla təsdiq) ----

def test_integration_real_request_429():
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/x", dependencies=[Depends(ratelimit.rate_limit("t_int", 1, 60.0))])
    async def x():
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/x").status_code == 200
    r = client.get("/x")
    assert r.status_code == 429
    assert "retry-after" in {k.lower() for k in r.headers}
