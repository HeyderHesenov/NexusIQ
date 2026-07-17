"""Şəxsi digest API — "Mənə Aid". Server heç nə saxlamır (localStorage-first).

Klient watchlist açarlarını + son-baxış vaxtını (epoch ms) göndərir; cavab yalnız
həmin aktivlərə toxunan xəbərlərdir. Rate-limit per-IP.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_user
from app.core.ratelimit import rate_limit
from app.db.session import get_db
from app.services import watchlist_intel

router = APIRouter()

# Epoch ms üst həddi ≈ 2100-01-01. Sərhədsiz `int` `datetime.fromtimestamp`-ı
# `ValueError: year is out of range` ilə partladırdı → tutulmamış 500.
_MAX_EPOCH_MS = 4_102_444_800_000
# Aktiv açarı: reyestr açarı (btc, nvda) və ya dinamik coin (c_<base>).
# `NewsAsset.asset_key` String(32) — eyni tavan.
_KEY_RE = r"^[A-Za-z0-9_.\-=^]{1,32}$"
# Miqdar/qiymət üçün ağlabatan tavan. `allow_inf_nan=False` HƏLLEDİCİDİR:
# JSON `1e999` Python-da `float('inf')`-ə çevrilir, `_num`-un NaN qorusu
# (`v == v`) isə inf-i BURAXIR (inf == inf → True) və inf `qty > 0`
# yoxlamasından da keçir → portfel riyaziyyatı səssizcə null/NaN-a çevrilir.
_MAX_NUM = 1e12


def _to_dt(epoch_ms: int | None) -> datetime | None:
    if not epoch_ms or epoch_ms <= 0:
        return None
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)


class IntelRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    keys: list[str] = Field(default_factory=list, max_length=60)
    last_seen: int | None = Field(
        default=None, alias="lastSeen", ge=0, le=_MAX_EPOCH_MS
    )  # epoch ms


class Holding(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(..., pattern=_KEY_RE)
    qty: float = Field(..., gt=0, le=_MAX_NUM, allow_inf_nan=False)
    avg_cost: float | None = Field(
        default=None, alias="avgCost", ge=0, le=_MAX_NUM, allow_inf_nan=False
    )


class PortfolioRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    holdings: list[Holding] = Field(default_factory=list, max_length=60)
    last_seen: int | None = Field(
        default=None, alias="lastSeen", ge=0, le=_MAX_EPOCH_MS
    )


@router.post(
    "",
    dependencies=[
        Depends(rate_limit("watchlist_intel", limit=30, window=60.0)),
        Depends(require_user),
    ],
)
async def watchlist_digest(
    req: IntelRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """İzlənən aktivlərə toxunan xəbərlərin şəxsi digesti."""
    return await watchlist_intel.digest(db, req.keys, _to_dt(req.last_seen))


@router.post(
    "/portfolio",
    dependencies=[
        Depends(rate_limit("portfolio_intel", limit=30, window=60.0)),
        Depends(require_user),
    ],
)
async def portfolio_intel(
    req: PortfolioRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Portfel P&L + bugünkü xəbərlərin pul-çəkili sıralanması (server heç nə saxlamır)."""
    holdings = [
        {"key": h.key, "qty": h.qty, "avgCost": h.avg_cost} for h in req.holdings
    ]
    return await watchlist_intel.portfolio(db, holdings, _to_dt(req.last_seen))


@router.get(
    "/{key}",
    dependencies=[
        Depends(rate_limit("watchlist_intel_asset", limit=60, window=60.0)),
        Depends(require_user),
    ],
)
async def asset_digest(
    key: str,
    last_seen: int | None = Query(None, alias="lastSeen", ge=0, le=_MAX_EPOCH_MS),
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
