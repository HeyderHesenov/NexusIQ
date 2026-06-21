"""Anomaliya route-ları — cari qiymət/həcm sıçrayışları."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.analytics import anomaly

router = APIRouter()


@router.get("")
async def current_anomalies(refresh: bool = Query(False)) -> list[dict]:
    """İzlənən aktivlərdə cari anomaliyalar (5 dəq keş; refresh=true məcburi)."""
    return await anomaly.scan_all(force=refresh)
