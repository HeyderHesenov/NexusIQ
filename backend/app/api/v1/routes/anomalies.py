"""Anomaliya route-ları — cari qiymət/həcm sıçrayışları."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import anomaly, anomaly_news
from app.db.session import get_db
from app.schemas.news import NewsOut

router = APIRouter()


@router.get("")
async def current_anomalies(refresh: bool = Query(False)) -> dict:
    """İzlənən aktivlərdə cari anomaliyalar + müşahidə siyahısı + statistika.

    Forma: `{asof, anomalies[], near[], stats{universe, anomalies, near}}`.
    5 dəq SWR keş; `refresh=true` məcburi yeniləmə.
    """
    return await anomaly.scan_all(force=refresh)


@router.get("/{key}/news", response_model=list[NewsOut])
async def anomaly_cause_news(
    key: str,
    k: int = Query(3, ge=1, le=5),
    db: AsyncSession = Depends(get_db),
) -> list[NewsOut]:
    """Anomaliyanın ehtimal olunan səbəbi — aktivi qeyd edən son xəbərlər (pulsuz)."""
    rows = await anomaly_news.news_for_asset(db, key, k=k)
    return [NewsOut.from_model(n) for n in rows]
