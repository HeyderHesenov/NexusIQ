"""Proqnoz doğruluq kartı API — açıq "biz nə qədər doğru çıxdıq" (trust layer)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.analytics import accuracy
from app.core.ratelimit import rate_limit

router = APIRouter()


@router.get(
    "",
    dependencies=[Depends(rate_limit("accuracy", limit=30, window=60.0))],
)
async def get_scorecard(
    by: str = Query("category", description="category|asset|direction|horizon"),
    horizon: int = Query(5, description="1|5|30 ticarət günü"),
) -> dict:
    """Proqnoz uğur nisbəti — slice üzrə, hər biri naiv baza ilə müqayisədə."""
    return await accuracy.scorecard(by, horizon)
