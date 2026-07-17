"""Korrelyasiya route-ları — matris (heatmap) + cüt analizi (chart + AI izah)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.agents import correlation_ai
from app.analytics import correlation
from app.core.auth import require_user
from app.core.budget import ai_budget
from app.core.ratelimit import rate_limit

router = APIRouter()

_LANGS = {"az", "en", "ru", "tr"}


@router.get("/matrix")
async def matrix(window: int = Query(90, ge=7, le=365)) -> dict:
    """Bütün aktivlər üçün Pearson korrelyasiya matrisi (UI heatmap)."""
    return await correlation.get_matrix(window)


@router.get("/pair")
async def pair(
    a: str = Query(..., min_length=1),
    b: str = Query(..., min_length=1),
    window: int = Query(90, ge=7, le=365),
) -> dict:
    """İki aktiv: Pearson dəyəri + normallaşmış seriyalar (AI izahı YOX — sürətli).

    AI izahı ayrıca `/pair/explain` ilə yüklənir ki, qrafik dərhal gəlsin və
    pəncərə dəyişəndə səhifə 3-4 saniyə AI-ı gözləyib donmasın.
    """
    result = await correlation.get_pair(a, b, window)
    if result is None:
        raise HTTPException(status_code=404, detail="Cüt üçün məlumat tapılmadı.")
    return result


@router.get(
    "/pair/explain",
    dependencies=[
        Depends(rate_limit("corr_explain", limit=20, window=60.0)),
        Depends(require_user),
        Depends(ai_budget("correlation_explain", weight=1)),
    ],
)
async def pair_explain(
    a: str = Query(..., min_length=1),
    b: str = Query(..., min_length=1),
    window: int = Query(90, ge=7, le=365),
    lang: str = Query("az"),
) -> dict:
    """Cüt üçün yalnız AI izahı (qrafikdən ayrı, keşli). Yavaş ola bilər."""
    lang = lang if lang in _LANGS else "az"
    result = await correlation.get_pair(a, b, window)
    if result is None:
        raise HTTPException(status_code=404, detail="Cüt üçün məlumat tapılmadı.")
    explanation = await correlation_ai.explain(
        result["a"]["label"], result["b"]["label"], result["value"], lang
    )
    return {"explanation": explanation}
