"""Anomaliya route-ları — cari qiymət/həcm sıçrayışları."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.analytics import anomaly

router = APIRouter()


@router.get("")
async def current_anomalies(refresh: bool = Query(False)) -> dict:
    """İzlənən aktivlərdə cari anomaliyalar + müşahidə siyahısı + statistika.

    Forma: `{asof, anomalies[], near[], stats{universe, anomalies, near}}`.
    5 dəq SWR keş; `refresh=true` məcburi yeniləmə.
    """
    return await anomaly.scan_all(force=refresh)
