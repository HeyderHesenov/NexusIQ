"""Aktiv route-ları — reyestr, canlı qiymət, tarixçə (watchlist/asset/compare)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import assets
from app.core.ratelimit import rate_limit
from app.db.session import get_db
from app.services import asset_news

router = APIRouter()

# `/{key}/news` qardaşında 60/60 var idi, bu ikisi isə TAMAMİLƏ limitsiz idi —
# halbuki hər ikisi keş boş/bayat olanda `asyncio.to_thread` ilə yfinance-ə
# çıxır. `/{key}` iki dəfə (quote + history) → 2× gücləndirici.
_asset_limit = rate_limit("asset_read", limit=60, window=60.0)
_registry_limit = rate_limit("asset_registry", limit=30, window=60.0)


@router.get("", dependencies=[Depends(_registry_limit)])
async def all_assets() -> list[dict]:
    """İzlənə bilən aktivlərin reyestri + Binance top coinlər."""
    return await assets.list_assets()


@router.get("/overview", dependencies=[Depends(_registry_limit)])
async def overview() -> list[dict]:
    """Bütün aktivlər — qiymət + 24s dəyişim + sparkline (CMC tərzi cədvəl)."""
    return await assets.get_overview()


@router.get("/{key}/quote", dependencies=[Depends(_asset_limit)])
async def asset_quote(key: str) -> dict:
    """Tək aktivin canlı qiyməti."""
    q = await assets.get_quote(key)
    if q is None:
        raise HTTPException(status_code=404, detail="Aktiv tapılmadı")
    return q


@router.get(
    "/{key}/news",
    dependencies=[Depends(rate_limit("asset_news", limit=60, window=60.0))],
)
async def asset_news_route(
    key: str,
    limit: int = Query(8, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Aktivə aid xəbərlər — DB-first (news_asset), boşluqda Yahoo ehtiyatı."""
    return await asset_news.for_asset(db, key.strip(), limit=limit)


@router.get("/{key}", dependencies=[Depends(_asset_limit)])
async def asset_detail(
    key: str, range: str = Query("3mo")
) -> dict:
    """Aktiv: canlı qiymət + tarixi seriya (chart üçün)."""
    quote = await assets.get_quote(key)
    history = await assets.get_history(key, range)
    if quote is None and history is None:
        raise HTTPException(status_code=404, detail="Aktiv tapılmadı")
    return {"quote": quote, "history": history}
