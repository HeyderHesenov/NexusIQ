"""Aktiv route-ları — reyestr, canlı qiymət, tarixçə (watchlist/asset/compare)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import assets
from app.core.ratelimit import rate_limit
from app.db.session import get_db
from app.services import asset_news

router = APIRouter()


@router.get("")
async def all_assets() -> list[dict]:
    """İzlənə bilən aktivlərin reyestri + Binance top coinlər."""
    return await assets.list_assets()


@router.get("/overview")
async def overview() -> list[dict]:
    """Bütün aktivlər — qiymət + 24s dəyişim + sparkline (CMC tərzi cədvəl)."""
    return await assets.get_overview()


@router.get("/{key}/quote")
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


@router.get("/{key}")
async def asset_detail(
    key: str, range: str = Query("3mo")
) -> dict:
    """Aktiv: canlı qiymət + tarixi seriya (chart üçün)."""
    quote = await assets.get_quote(key)
    history = await assets.get_history(key, range)
    if quote is None and history is None:
        raise HTTPException(status_code=404, detail="Aktiv tapılmadı")
    return {"quote": quote, "history": history}
