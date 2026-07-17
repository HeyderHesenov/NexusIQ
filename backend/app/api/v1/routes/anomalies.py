"""Anomaliya route-ları — cari qiymət/həcm sıçrayışları."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import anomaly, anomaly_news
from app.core.ratelimit import rate_limit
from app.db.session import get_db
from app.schemas.news import NewsOut

router = APIRouter()

# Keş oxunuşu ucuzdur, amma endpoint tamamilə limitsiz idi.
_list_limit = rate_limit("anomaly_list", limit=60, window=60.0)
# `refresh=true` KEŞİ KEÇİR → bütün universum üzrə tam yfinance yenidən skanı.
# Ayrıca, sərt bucket (bax radar.py-dakı eyni əsaslandırma).
_force_limit = rate_limit("anomaly_refresh", limit=5, window=60.0)


@router.get("", dependencies=[Depends(_list_limit)])
async def current_anomalies(
    request: Request, refresh: bool = Query(False)
) -> dict:
    """İzlənən aktivlərdə cari anomaliyalar + müşahidə siyahısı + statistika.

    Forma: `{asof, anomalies[], near[], stats{universe, anomalies, near}}`.
    5 dəq SWR keş; `refresh=true` məcburi yeniləmə.
    """
    if refresh:
        # Limit MƏHZ bahalı budaqda — ucuz keş oxunuşu cəzalandırılmır.
        await _force_limit(request)
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
