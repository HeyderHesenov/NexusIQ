"""/me/bookmarks News-i serializasiya edərkən `source`-u eager-load etməlidir.

Reqressiya qoruyucusu: `NewsOut.from_model` `n.source.name`-ə toxunur. Sorğu
`selectinload(News.source)` etməzsə, async-də yüklənməmiş relationship
`sqlalchemy.exc.MissingGreenlet` atır → bütün /me/bookmarks 500 (əvvəl belə idi).
Bu test bookmark-lı istifadəçi üçün 200 + düzgün mənbə adı tələb edir.
"""
from __future__ import annotations

from app.core import cookies
from app.models import News, Source

ME = "/api/v1/me"
AUTH = "/api/v1/auth"
PW = "testpassword123"


def _csrf(client):
    return {"X-CSRF-Token": client.cookies.get(cookies.csrf_name())}


async def _login(client, email):
    client.cookies.clear()
    await client.post(f"{AUTH}/register", json={"email": email, "password": PW})
    await client.post(f"{AUTH}/login", json={"email": email, "password": PW})


async def test_bookmarks_serialize_source_without_missing_greenlet(client, db):
    # Mənbəli xəbər — source relationship-i məhz burada eager-load olunmalıdır.
    src = Source(name="TestWire", default_category="us")
    db.add(src)
    await db.flush()
    news = News(
        title="Bookmarked headline",
        url="https://example.com/a1",
        category="us",
        dedup_hash="bm-hash-1",
        source_id=src.id,
    )
    db.add(news)
    await db.commit()

    await _login(client, "bookmarker@example.com")
    r = await client.post(f"{ME}/bookmarks/{news.id}", headers=_csrf(client))
    assert r.status_code == 200

    r2 = await client.get(f"{ME}/bookmarks")
    assert r2.status_code == 200  # MissingGreenlet olsa 500 olardı
    body = r2.json()
    assert len(body) == 1
    assert body[0]["source"] == "TestWire"  # source eager-load olundu + serializasiya
    assert body[0]["id"] == str(news.id)
