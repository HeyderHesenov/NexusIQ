"""Şəxsi digest API — "Mənə Aid". Server heç nə saxlamır (localStorage-first).

Klient watchlist açarlarını + son-baxış vaxtını (epoch ms) göndərir; cavab yalnız
həmin aktivlərə toxunan xəbərlərdir. Rate-limit per-IP.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ratelimit import rate_limit
from app.db.session import get_db
from app.services import watchlist_intel

router = APIRouter()


def _to_dt(epoch_ms: int | None) -> datetime | None:
    if not epoch_ms or epoch_ms <= 0:
        return None
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)


class IntelRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    keys: list[str] = Field(default_factory=list, max_length=60)
    last_seen: int | None = Field(default=None, alias="lastSeen")  # epoch ms


@router.post("", dependencies=[Depends(rate_limit("watchlist_intel", limit=30, window=60.0))])
async def watchlist_digest(
    req: IntelRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """İzlənən aktivlərə toxunan xəbərlərin şəxsi digesti."""
    return await watchlist_intel.digest(db, req.keys, _to_dt(req.last_seen))


@router.get(
    "/{key}",
    dependencies=[Depends(rate_limit("watchlist_intel_asset", limit=60, window=60.0))],
)
async def asset_digest(
    key: str,
    last_seen: int | None = Query(None, alias="lastSeen"),
    days: int = Query(30, ge=1, le=120),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Tək aktiv üçün digest (drill-down /mene-aid səhifəsi)."""
    from datetime import timedelta

    since = datetime.now(timezone.utc) - timedelta(days=days)
    d = await watchlist_intel.asset_digest(
        db, key.strip(), since, _to_dt(last_seen), per_asset=20, days=days
    )
    return d or {"key": key, "label": key.upper(), "count": 0, "news": [], "trust": None}
