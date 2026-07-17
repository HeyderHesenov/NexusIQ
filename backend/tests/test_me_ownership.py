"""/me/* sahiblik izolyasiyası (IDOR). B → A-nın sətrinə 404 (403 DEYİL — enumerasiya orakulu).

Kök səbəb: user data-nı serverə köçürmək təhlükəsizlik reqressiyasıdır — bir unudulmuş
WHERE user_id hamını açır. İzolyasiya MEXANİKİ icra olunmalıdır; bu testlər onu pinləyir.
"""
from __future__ import annotations

import pytest

from app.core import cookies

ME = "/api/v1/me"
AUTH = "/api/v1/auth"
PW = "testpassword123"


def _csrf(client):
    return {"X-CSRF-Token": client.cookies.get(cookies.csrf_name())}


async def _login(client, email):
    client.cookies.clear()  # əvvəlki istifadəçinin cookie-si stale qalmasın (CSRF/kimlik)
    await client.post(f"{AUTH}/register", json={"email": email, "password": PW})
    await client.post(f"{AUTH}/login", json={"email": email, "password": PW})


async def test_unauthenticated_me_401(client):
    r = await client.get(f"{ME}/watchlist")
    assert r.status_code == 401


async def test_watchlist_isolation(client):
    await _login(client, "a@example.com")
    await client.post(f"{ME}/watchlist/btc", headers=_csrf(client))
    await _login(client, "b@example.com")  # B-yə keç
    await client.post(f"{ME}/watchlist/eth", headers=_csrf(client))
    r = await client.get(f"{ME}/watchlist")
    assert r.json()["keys"] == ["eth"]  # A-nın btc-si görünmür


async def test_alert_idor_404_not_403(client):
    await _login(client, "a@example.com")
    r = await client.post(
        f"{ME}/alerts", headers=_csrf(client),
        json={"assetKey": "btc", "direction": "above", "price": "100"},
    )
    assert r.status_code == 200
    alert_id = r.json()["id"]

    await _login(client, "b@example.com")  # B kimi A-nın alert-ini silməyə çalış
    r2 = await client.delete(f"{ME}/alerts/{alert_id}", headers=_csrf(client))
    assert r2.status_code == 404  # 403 DEYİL


async def test_holdings_isolation(client):
    await _login(client, "a@example.com")
    await client.put(f"{ME}/holdings/btc", headers=_csrf(client), json={"qty": "1.5"})
    await _login(client, "b@example.com")
    r = await client.get(f"{ME}/holdings")
    assert r.json() == []  # B-nin heç nəyi yoxdur


async def test_bookmark_isolation_and_missing_news_skipped(client):
    await _login(client, "a@example.com")
    # mövcud olmayan xəbər id → skip (200, əlavə olunmur)
    r = await client.post(f"{ME}/bookmarks/999999999", headers=_csrf(client))
    assert r.status_code == 200
    r2 = await client.get(f"{ME}/bookmarks")
    assert r2.json() == []
