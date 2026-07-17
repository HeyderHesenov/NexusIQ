"""AI büdcə nəzarəti — request səviyyəsində. ai_budget dependency + qlobal cap + kill switch.

Per-user gündəlik DB-dən (deploy-da sıfırlanan büdcə büdcə deyil). Qlobal cap 60s keş
(60s stale ən çox 60s xərc). Kill switch 30s keş, system_flags-dan (3 a.m.-də saniyələrlə
qanı dayandırmaq üçün). Bounded overshoot (99/100 → ~103) qəbul edilir.
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models import AiUsage, SystemFlag

logger = logging.getLogger("nexusiq.budget")

_KILL_KEY = "ai_enabled"
_GLOBAL_TTL = 60.0
_FLAG_TTL = 30.0

_global_cache: dict = {"val": None, "exp": 0.0}
_flag_cache: dict[str, tuple[bool, float]] = {}


def _clear_caches() -> None:
    _global_cache["val"] = None
    _global_cache["exp"] = 0.0
    _flag_cache.clear()


def _day_start() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


async def global_daily_used(session: AsyncSession) -> int:
    return int(
        await session.scalar(
            select(func.coalesce(func.sum(AiUsage.weight), 0)).where(
                AiUsage.created_at >= _day_start()
            )
        )
    )


async def user_daily_used(session: AsyncSession, user_id: uuid.UUID) -> int:
    return int(
        await session.scalar(
            select(func.coalesce(func.sum(AiUsage.weight), 0)).where(
                AiUsage.created_at >= _day_start(), AiUsage.user_id == user_id
            )
        )
    )


async def _global_cached(session: AsyncSession) -> int:
    now = time.monotonic()
    if _global_cache["val"] is not None and _global_cache["exp"] > now:
        return _global_cache["val"]
    v = await global_daily_used(session)
    _global_cache["val"] = v
    _global_cache["exp"] = now + _GLOBAL_TTL
    return v


async def is_ai_enabled(session: AsyncSession) -> bool:
    now = time.monotonic()
    ent = _flag_cache.get(_KILL_KEY)
    if ent and ent[1] > now:
        return ent[0]
    row = await session.scalar(select(SystemFlag.value).where(SystemFlag.key == _KILL_KEY))
    enabled = row is None or row.strip().lower() != "false"  # default: aktiv
    _flag_cache[_KILL_KEY] = (enabled, now + _FLAG_TTL)
    return enabled


async def set_flag(session: AsyncSession, key: str, value: str, *, by: str | None = None) -> None:
    await session.execute(
        pg_insert(SystemFlag)
        .values(key=key, value=value, updated_by=by)
        .on_conflict_do_update(index_elements=["key"], set_={"value": value, "updated_by": by})
    )
    _flag_cache.pop(key, None)  # dərhal təsir (deploy tələb etmir)


async def record_usage(
    session: AsyncSession, route: str, weight: int, *, user_id: uuid.UUID | None = None
) -> None:
    """Bir billable request. user_id=None → planlayıcı/sistem (qlobal cap-a sayılır)."""
    session.add(AiUsage(route=route[:48], weight=weight, user_id=user_id))


async def record_system_usage(route: str, weight: int) -> None:
    """Planlayıcı istifadəsi (user_id=NULL) — öz session-u, qlobal cap-a sayılır.
    Planlayıcı ən böyük xərcləyicidir; sayılmasa qlobal cap yalandır."""
    if weight <= 0:
        return
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as s:
        await record_usage(s, route, weight, user_id=None)
        await s.commit()
    _clear_caches()  # qlobal keş dərhal yenilənsin


def _err(code: str) -> HTTPException:
    return HTTPException(status_code=503, detail={"code": code})


def ai_budget(route: str, weight: int = 1):
    """Route dependency — admission-da yoxlayır + ai_usage yazır. Aşılırsa 503."""

    async def _dep(request: Request, db: AsyncSession = Depends(get_db)) -> None:
        if not await is_ai_enabled(db):
            raise _err("ai_disabled")

        if await _global_cached(db) + weight > settings.ai_global_daily_calls:
            logger.critical("Qlobal AI cap aşıldı (route=%s)", route)
            raise _err("ai_budget_exhausted")

        uid_raw = getattr(request.state, "user_id", None)
        uid = uuid.UUID(uid_raw) if uid_raw else None
        if uid is not None:
            if await user_daily_used(db, uid) + weight > settings.ai_daily_calls_per_user:
                raise _err("ai_budget_exhausted")

        await record_usage(db, route, weight, user_id=uid)
        await db.commit()
        if _global_cache["val"] is not None:  # bounded overshoot üçün keşi artır
            _global_cache["val"] += weight

    return _dep
