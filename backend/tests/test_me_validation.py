"""/me/* input validasiyası — inf/NaN/mənfi, açar, cap, href, import.

Kök səbəb: klient-supplied data serverdə saxlanılır → validasiya İKİ qatda olmalıdır
(Pydantic + DB CHECK). Bu testlər hər ikisini pinləyir (canlı Infinity bug daxil).
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.core import cookies

ME = "/api/v1/me"
AUTH = "/api/v1/auth"
PW = "testpassword123"


def _csrf(client):
    return {"X-CSRF-Token": client.cookies.get(cookies.csrf_name())}


async def _login(client, email="v@example.com"):
    await client.post(f"{AUTH}/register", json={"email": email, "password": PW})
    await client.post(f"{AUTH}/login", json={"email": email, "password": PW})


async def _put_qty_raw(client, raw_body: bytes):
    return await client.put(
        f"{ME}/holdings/btc",
        headers={**_csrf(client), "Content-Type": "application/json"},
        content=raw_body,
    )


async def test_holding_infinity_rejected(client):
    await _login(client)
    r = await _put_qty_raw(client, b'{"qty": 1e400}')  # JSON Infinity → canlı bug
    assert r.status_code == 422


async def test_holding_nan_zero_negative_overmax_rejected(client):
    await _login(client)
    for body in (b'{"qty": NaN}', b'{"qty": 0}', b'{"qty": -1}', b'{"qty": 1e13}'):
        r = await _put_qty_raw(client, body)
        assert r.status_code == 422, body


async def test_avg_cost_infinity_rejected(client):
    await _login(client)
    r = await _put_qty_raw(client, b'{"qty": 1, "avgCost": 1e400}')
    assert r.status_code == 422


async def test_bad_asset_key_rejected(client):
    await _login(client)
    r = await client.put(f"{ME}/holdings/{'x' * 33}", headers=_csrf(client), json={"qty": "1"})
    assert r.status_code == 422
    # routeable amma qeyri-qanuni simvol ($) → _key rədd edir (422, routing 404 deyil)
    r2 = await client.put(f"{ME}/holdings/in$valid", headers=_csrf(client), json={"qty": "1"})
    assert r2.status_code == 422


async def test_watchlist_cap(client):
    await _login(client)
    # 60 fərqli açar → OK, 61-ci → 409
    for i in range(60):
        r = await client.post(f"{ME}/watchlist/k{i}", headers=_csrf(client))
        assert r.status_code == 200
    r = await client.post(f"{ME}/watchlist/k60", headers=_csrf(client))
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "cap_exceeded"


async def test_saved_event_href_validated(client):
    await _login(client)
    for href in ("//evil.com", "javascript:alert(1)", "https://evil.com"):
        r = await client.post(
            f"{ME}/saved-events", headers=_csrf(client),
            json={"eventKey": "e1", "payload": {"href": href}},
        )
        assert r.status_code == 422, href
    # düzgün daxili href → OK
    r = await client.post(
        f"{ME}/saved-events", headers=_csrf(client),
        json={"eventKey": "e1", "payload": {"href": "/markets"}},
    )
    assert r.status_code == 200


async def test_db_check_rejects_nan_raw_insert(db):
    # Pydantic-i tam keçib birbaşa INSERT → DB CHECK tutmalı (layered müdafiə).
    from app.models import User, UserHolding

    u = User(email="rawnan@example.com", password_hash=None)
    db.add(u)
    await db.flush()
    db.add(UserHolding(user_id=u.id, asset_key="btc", qty=Decimal("NaN")))
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_import_skips_bad_items(client):
    await _login(client)
    payload = {
        "watchlist": ["btc", "eth", "x" * 40],  # 3-cü açar yararsız
        "holdings": [
            {"key": "btc", "qty": "1.5"},
            {"key": "eth", "qty": "not-a-number"},  # yararsız
        ],
        "savedEvents": [
            {"eventKey": "ok", "payload": {"href": "/x"}},
            {"eventKey": "bad", "payload": {"href": "//evil"}},  # yararsız href
        ],
    }
    r = await client.post(f"{ME}/import", headers=_csrf(client), json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["skipped"] >= 3 and body["imported"] >= 3
    # ikinci dəfə → idempotent (heç nə partlamır)
    r2 = await client.post(f"{ME}/import", headers=_csrf(client), json=payload)
    assert r2.status_code == 200
