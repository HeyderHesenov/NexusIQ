"""Per-user data CRUD + caps + additiv import. İzolyasiya service qatında (RLS yox).

Hər əməliyyat user_id ilə scope-lanır; heç vaxt unscoped get_by_id yoxdur.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    News,
    UserAlert,
    UserBookmark,
    UserHolding,
    UserPrefs,
    UserSavedEvent,
    UserWatchlist,
)

WATCH_CAP = 60
HOLD_CAP = 60
BOOKMARK_CAP = 200
ALERT_CAP = 50
SAVED_CAP = 100


class CapExceeded(Exception):
    def __init__(self, what: str) -> None:
        super().__init__(what)
        self.what = what


async def _count(session, model, user_id) -> int:
    return await session.scalar(
        select(func.count()).select_from(model).where(model.user_id == user_id)
    )


# ---- Watchlist ----

async def list_watchlist(session: AsyncSession, user_id) -> list[str]:
    rows = await session.scalars(
        select(UserWatchlist.asset_key)
        .where(UserWatchlist.user_id == user_id)
        .order_by(UserWatchlist.created_at)
    )
    return list(rows)


async def add_watch(session: AsyncSession, user_id, key: str, *, enforce_cap=True) -> bool:
    exists = await session.scalar(
        select(UserWatchlist.id).where(
            UserWatchlist.user_id == user_id, UserWatchlist.asset_key == key
        )
    )
    if exists:
        return False
    if enforce_cap and await _count(session, UserWatchlist, user_id) >= WATCH_CAP:
        raise CapExceeded("watchlist")
    await session.execute(
        pg_insert(UserWatchlist)
        .values(user_id=user_id, asset_key=key)
        .on_conflict_do_nothing(index_elements=["user_id", "asset_key"])
    )
    return True


async def remove_watch(session: AsyncSession, user_id, key: str) -> None:
    await session.execute(
        delete(UserWatchlist).where(
            UserWatchlist.user_id == user_id, UserWatchlist.asset_key == key
        )
    )


# ---- Holdings ----

async def list_holdings(session: AsyncSession, user_id) -> list[UserHolding]:
    rows = await session.scalars(
        select(UserHolding).where(UserHolding.user_id == user_id).order_by(UserHolding.created_at)
    )
    return list(rows)


async def upsert_holding(
    session: AsyncSession, user_id, key: str, qty: Decimal, avg_cost: Decimal | None, *, enforce_cap=True
) -> None:
    exists = await session.scalar(
        select(UserHolding.id).where(
            UserHolding.user_id == user_id, UserHolding.asset_key == key
        )
    )
    if not exists and enforce_cap and await _count(session, UserHolding, user_id) >= HOLD_CAP:
        raise CapExceeded("holdings")
    await session.execute(
        pg_insert(UserHolding)
        .values(user_id=user_id, asset_key=key, qty=qty, avg_cost=avg_cost)
        .on_conflict_do_update(
            index_elements=["user_id", "asset_key"],
            set_={"qty": qty, "avg_cost": avg_cost},
        )
    )


async def remove_holding(session: AsyncSession, user_id, key: str) -> None:
    await session.execute(
        delete(UserHolding).where(
            UserHolding.user_id == user_id, UserHolding.asset_key == key
        )
    )


# ---- Bookmarks ----

async def add_bookmark(session: AsyncSession, user_id, news_id: int, *, enforce_cap=True) -> bool:
    # Silinmiş xəbəri atla (FK CASCADE-dən əvvəl mövcudluq).
    if not await session.scalar(select(News.id).where(News.id == news_id)):
        return False
    exists = await session.scalar(
        select(UserBookmark.id).where(
            UserBookmark.user_id == user_id, UserBookmark.news_id == news_id
        )
    )
    if exists:
        return False
    if enforce_cap and await _count(session, UserBookmark, user_id) >= BOOKMARK_CAP:
        raise CapExceeded("bookmarks")
    await session.execute(
        pg_insert(UserBookmark)
        .values(user_id=user_id, news_id=news_id)
        .on_conflict_do_nothing(index_elements=["user_id", "news_id"])
    )
    return True


async def remove_bookmark(session: AsyncSession, user_id, news_id: int) -> None:
    await session.execute(
        delete(UserBookmark).where(
            UserBookmark.user_id == user_id, UserBookmark.news_id == news_id
        )
    )


async def list_bookmark_news_ids(session: AsyncSession, user_id) -> list[int]:
    rows = await session.scalars(
        select(UserBookmark.news_id)
        .where(UserBookmark.user_id == user_id)
        .order_by(UserBookmark.created_at.desc())
    )
    return list(rows)


# ---- Alerts ----

async def list_alerts(session: AsyncSession, user_id) -> list[UserAlert]:
    rows = await session.scalars(
        select(UserAlert).where(UserAlert.user_id == user_id).order_by(UserAlert.created_at.desc())
    )
    return list(rows)


async def create_alert(
    session: AsyncSession, user_id, *, asset_key, label, direction, price, enforce_cap=True
) -> UserAlert | None:
    if enforce_cap and await _count(session, UserAlert, user_id) >= ALERT_CAP:
        raise CapExceeded("alerts")
    # Dublikat (eyni açar/istiqamət/qiymət) → skip.
    dup = await session.scalar(
        select(UserAlert.id).where(
            UserAlert.user_id == user_id,
            UserAlert.asset_key == asset_key,
            UserAlert.direction == direction,
            UserAlert.price == price,
        )
    )
    if dup:
        return None
    alert = UserAlert(
        user_id=user_id, asset_key=asset_key, label=label, direction=direction, price=price
    )
    session.add(alert)
    await session.flush()
    return alert


async def delete_alert(session: AsyncSession, user_id, alert_id) -> bool:
    obj = await session.scalar(
        select(UserAlert).where(UserAlert.id == alert_id, UserAlert.user_id == user_id)
    )
    if obj is None:
        return False
    await session.delete(obj)
    return True


# ---- Saved events ----

async def list_saved(session: AsyncSession, user_id) -> list[UserSavedEvent]:
    rows = await session.scalars(
        select(UserSavedEvent)
        .where(UserSavedEvent.user_id == user_id)
        .order_by(UserSavedEvent.saved_at.desc())
    )
    return list(rows)


async def upsert_saved(
    session: AsyncSession, user_id, event_key: str, payload: dict, *, enforce_cap=True
) -> bool:
    exists = await session.scalar(
        select(UserSavedEvent.id).where(
            UserSavedEvent.user_id == user_id, UserSavedEvent.event_key == event_key
        )
    )
    if not exists and enforce_cap and await _count(session, UserSavedEvent, user_id) >= SAVED_CAP:
        raise CapExceeded("saved_events")
    await session.execute(
        pg_insert(UserSavedEvent)
        .values(user_id=user_id, event_key=event_key, payload=payload)
        .on_conflict_do_update(
            index_elements=["user_id", "event_key"], set_={"payload": payload}
        )
    )
    return True


async def remove_saved(session: AsyncSession, user_id, event_key: str) -> None:
    await session.execute(
        delete(UserSavedEvent).where(
            UserSavedEvent.user_id == user_id, UserSavedEvent.event_key == event_key
        )
    )


# ---- Prefs ----

async def get_prefs(session: AsyncSession, user_id) -> UserPrefs | None:
    return await session.scalar(select(UserPrefs).where(UserPrefs.user_id == user_id))


async def upsert_prefs(session: AsyncSession, user_id, **fields) -> None:
    clean = {k: v for k, v in fields.items() if v is not None}
    if not clean:
        return
    await session.execute(
        pg_insert(UserPrefs)
        .values(user_id=user_id, **clean)
        .on_conflict_do_update(index_elements=["user_id"], set_=clean)
    )
