"""/me/* — per-user data (watchlist/holdings/bookmarks/alerts/saved/prefs) + import + intel.

Bütün route-lar require_user (router səviyyəsində). Sahiblik service qatında user_id
ilə scope-lanır. /me/intel/* mövcud watchlist_intel servisini işlədir — mənbə request
gövdəsindən DB-yə köçdü, servis dəyişmədi.
"""
from __future__ import annotations

import re
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import require_user
from app.db.session import get_db
from app.models import News, User
from app.schemas.me import (
    AlertIn,
    AlertOut,
    AuditOut,
    HoldingIn,
    HoldingOut,
    ImportIn,
    ImportOut,
    OkOut,
    PrefsIn,
    PrefsOut,
    SavedEventIn,
    SavedEventOut,
)
from app.schemas.news import NewsOut
from app.services import audit, user_data, watchlist_intel

router = APIRouter()

_KEY_RE = re.compile(r"^[a-z0-9_.\-=^]{1,32}$")


def _key(key: str) -> str:
    k = key.strip().lower()
    if not _KEY_RE.match(k):
        raise HTTPException(422, detail={"code": "invalid_key"})
    return k


def _cap_guard(exc: user_data.CapExceeded):
    raise HTTPException(409, detail={"code": "cap_exceeded", "what": exc.what})


# ==================== Watchlist ====================

@router.get("/watchlist")
async def get_watchlist(user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> dict:
    return {"keys": await user_data.list_watchlist(db, user.id)}


@router.post("/watchlist/{key}")
async def add_watchlist(key: str, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> dict:
    try:
        await user_data.add_watch(db, user.id, _key(key))
    except user_data.CapExceeded as e:
        _cap_guard(e)
    await db.commit()
    return OkOut().model_dump(by_alias=True)


@router.delete("/watchlist/{key}")
async def del_watchlist(key: str, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> dict:
    await user_data.remove_watch(db, user.id, _key(key))
    await db.commit()
    return OkOut().model_dump(by_alias=True)


# ==================== Holdings ====================

@router.get("/holdings")
async def get_holdings(user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = await user_data.list_holdings(db, user.id)
    return [
        HoldingOut(key=h.asset_key, qty=h.qty, avg_cost=h.avg_cost).model_dump(by_alias=True)
        for h in rows
    ]


@router.put("/holdings/{key}")
async def put_holding(
    key: str, payload: HoldingIn, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)
) -> dict:
    try:
        await user_data.upsert_holding(db, user.id, _key(key), payload.qty, payload.avg_cost)
    except user_data.CapExceeded as e:
        _cap_guard(e)
    await db.commit()
    return OkOut().model_dump(by_alias=True)


@router.delete("/holdings/{key}")
async def del_holding(key: str, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> dict:
    await user_data.remove_holding(db, user.id, _key(key))
    await db.commit()
    return OkOut().model_dump(by_alias=True)


# ==================== Bookmarks ====================

@router.get("/bookmarks")
async def get_bookmarks(user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    ids = await user_data.list_bookmark_news_ids(db, user.id)
    if not ids:
        return []
    # selectinload(News.source) MƏCBURİDİR: `NewsOut.from_model` `n.source.name`-ə
    # toxunur; async-də yüklənməmiş relationship = MissingGreenlet (bütün sorğu 500).
    # Digər BÜTÜN News-serializasiya sorğuları bunu edir (news.py `_BASE` və s.).
    rows = (
        await db.scalars(
            select(News).options(selectinload(News.source)).where(News.id.in_(ids))
        )
    ).all()
    by_id = {n.id: n for n in rows}
    return [NewsOut.from_model(by_id[i]).model_dump(by_alias=True) for i in ids if i in by_id]


@router.post("/bookmarks/{news_id}")
async def add_bookmark(news_id: int, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> dict:
    try:
        await user_data.add_bookmark(db, user.id, news_id)
    except user_data.CapExceeded as e:
        _cap_guard(e)
    await db.commit()
    return OkOut().model_dump(by_alias=True)


@router.delete("/bookmarks/{news_id}")
async def del_bookmark(news_id: int, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> dict:
    await user_data.remove_bookmark(db, user.id, news_id)
    await db.commit()
    return OkOut().model_dump(by_alias=True)


# ==================== Alerts ====================

def _alert_out(a) -> dict:
    return AlertOut(
        id=str(a.id), asset_key=a.asset_key, label=a.label, direction=a.direction,
        price=a.price, active=a.active,
        triggered_at=a.triggered_at.isoformat() if a.triggered_at else None,
    ).model_dump(by_alias=True)


@router.get("/alerts")
async def get_alerts(user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    return [_alert_out(a) for a in await user_data.list_alerts(db, user.id)]


@router.post("/alerts")
async def create_alert(
    payload: AlertIn, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)
) -> dict:
    try:
        alert = await user_data.create_alert(
            db, user.id, asset_key=_key(payload.asset_key), label=payload.label,
            direction=payload.direction, price=payload.price,
        )
    except user_data.CapExceeded as e:
        _cap_guard(e)
    await db.commit()
    return _alert_out(alert) if alert else OkOut().model_dump(by_alias=True)


@router.delete("/alerts/{alert_id}")
async def del_alert(
    alert_id: str = Path(...), user: User = Depends(require_user), db: AsyncSession = Depends(get_db)
) -> dict:
    ok = await user_data.delete_alert(db, user.id, alert_id)
    if not ok:
        raise HTTPException(404)  # 404 not 403 — enumerasiya orakulu yox
    await db.commit()
    return OkOut().model_dump(by_alias=True)


# ==================== Saved events ====================

@router.get("/saved-events")
async def get_saved(user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> list[dict]:
    return [
        SavedEventOut(
            event_key=s.event_key, payload=s.payload or {},
            saved_at=s.saved_at.isoformat() if s.saved_at else None,
        ).model_dump(by_alias=True)
        for s in await user_data.list_saved(db, user.id)
    ]


@router.post("/saved-events")
async def add_saved(
    payload: SavedEventIn, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)
) -> dict:
    try:
        await user_data.upsert_saved(
            db, user.id, payload.event_key, payload.payload.model_dump(by_alias=True)
        )
    except user_data.CapExceeded as e:
        _cap_guard(e)
    await db.commit()
    return OkOut().model_dump(by_alias=True)


@router.delete("/saved-events/{event_key}")
async def del_saved(event_key: str, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> dict:
    await user_data.remove_saved(db, user.id, event_key[:128])
    await db.commit()
    return OkOut().model_dump(by_alias=True)


# ==================== Prefs ====================

@router.get("/prefs")
async def get_prefs(user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> dict:
    p = await user_data.get_prefs(db, user.id)
    return PrefsOut(
        last_seen_at=p.last_seen_at.isoformat() if (p and p.last_seen_at) else None,
        lang=(p.lang if p else "az"),
        theme=(p.theme if p else None),
    ).model_dump(by_alias=True)


@router.put("/prefs")
async def put_prefs(
    payload: PrefsIn, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)
) -> dict:
    from datetime import datetime, timezone

    fields: dict = {}
    if payload.last_seen is not None:
        fields["last_seen_at"] = datetime.fromtimestamp(payload.last_seen / 1000, tz=timezone.utc)
    if payload.lang is not None:
        fields["lang"] = payload.lang
    if payload.theme is not None:
        fields["theme"] = payload.theme
    await user_data.upsert_prefs(db, user.id, **fields)
    await db.commit()
    return OkOut().model_dump(by_alias=True)


# ==================== Import (additiv) ====================

@router.post("/import")
async def import_data(
    payload: ImportIn, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)
) -> dict:
    """Additiv birləşmə (ON CONFLICT DO NOTHING). HEÇ VAXT silmir; yararsız elementi
    atlayır (bir pis sətir bütün portfeli bloklamamalıdır). Hər element SAVEPOINT-də
    izolyasiya olunur → xəta tranzaksiyanı zəhərləmir."""
    counts = {"imported": 0, "skipped": 0}

    async def _try(fn) -> None:
        try:
            async with db.begin_nested():
                added = await fn()
            counts["imported" if added else "skipped"] += 1
        except Exception:  # noqa: BLE001 — bir pis element bütün importu bloklamamalı
            counts["skipped"] += 1

    for key in payload.watchlist:
        await _try(lambda key=key: user_data.add_watch(db, user.id, _key(key)))

    for h in payload.holdings:
        async def _h(h=h):
            item = HoldingIn.model_validate(h)
            await user_data.upsert_holding(db, user.id, _key(str(h.get("key", ""))), item.qty, item.avg_cost)
            return True
        await _try(_h)

    for nid in payload.bookmarks:
        await _try(lambda nid=nid: user_data.add_bookmark(db, user.id, int(nid)))

    for a in payload.alerts:
        async def _a(a=a):
            item = AlertIn.model_validate(a)
            return bool(await user_data.create_alert(
                db, user.id, asset_key=_key(item.asset_key), label=item.label,
                direction=item.direction, price=item.price,
            ))
        await _try(_a)

    for ev in payload.saved_events:
        async def _e(ev=ev):
            item = SavedEventIn.model_validate(ev)
            await user_data.upsert_saved(db, user.id, item.event_key, item.payload.model_dump(by_alias=True))
            return True
        await _try(_e)

    await db.commit()
    return ImportOut(imported=counts["imported"], skipped=counts["skipped"]).model_dump(by_alias=True)


# ==================== Intel (mövcud servis, mənbə = DB) ====================

@router.get("/intel/watchlist")
async def intel_watchlist(user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> dict:
    keys = await user_data.list_watchlist(db, user.id)
    p = await user_data.get_prefs(db, user.id)
    return await watchlist_intel.digest(db, keys, p.last_seen_at if p else None)


@router.get("/intel/portfolio")
async def intel_portfolio(user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> dict:
    rows = await user_data.list_holdings(db, user.id)
    holdings = [
        {"key": h.asset_key, "qty": float(h.qty), "avgCost": float(h.avg_cost) if h.avg_cost is not None else None}
        for h in rows
    ]
    p = await user_data.get_prefs(db, user.id)
    return await watchlist_intel.portfolio(db, holdings, p.last_seen_at if p else None)


@router.get("/intel/asset/{key}")
async def intel_asset(key: str, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)) -> dict:
    from datetime import datetime, timedelta, timezone

    k = _key(key)
    p = await user_data.get_prefs(db, user.id)
    since = datetime.now(timezone.utc) - timedelta(days=30)
    d = await watchlist_intel.asset_digest(
        db, k, since, p.last_seen_at if p else None, per_asset=20, days=30
    )
    return d or {"key": k, "label": k.upper(), "count": 0, "news": [], "trust": None}


# ==================== Audit ("son fəaliyyət") ====================

@router.get("/audit")
async def get_audit(
    user: User = Depends(require_user), db: AsyncSession = Depends(get_db)
) -> list[dict]:
    """İstifadəçinin öz təhlükəsizlik hadisələri (login/parol/sessiya) — ən son 50."""
    rows = await audit.list_recent(db, user.id, limit=50)
    return [
        AuditOut(
            id=str(r.id),
            event=r.event,
            ip=r.ip,
            user_agent=r.user_agent,
            meta=r.meta,
            created_at=r.created_at.isoformat() if r.created_at else None,
        ).model_dump(by_alias=True)
        for r in rows
    ]
