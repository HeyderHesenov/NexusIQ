"""Radar route-ları — fürsət sıralaması + on-demand AI izahı (hibrid)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.agents import radar_ai
from app.analytics import radar
from app.core.ratelimit import rate_limit

router = APIRouter()

_LANGS = {"az", "en", "ru", "tr"}


@router.get("")
async def radar_list(
    category: str = Query("crypto"),
    refresh: bool = Query(False),
) -> list[dict]:
    """Kateqoriya üzrə fürsət balı ilə sıralanmış aktivlər (5 dəq keş)."""
    if category not in radar.TAB_CONFIG:
        raise HTTPException(status_code=404, detail="Naməlum kateqoriya")
    return await radar.get_radar(category, force=refresh)


@router.get(
    "/{key}/explain",
    dependencies=[Depends(rate_limit("radar_ai", limit=20, window=60.0))],
)
async def radar_explain(key: str, lang: str = Query("az")) -> dict:
    """Aktivin niyə radarda olduğunu AI ilə izah edir (yalnız istəklə)."""
    lang = lang if lang in _LANGS else "az"
    item, _ = await radar.find_item(key)
    if item is None:
        raise HTTPException(status_code=404, detail="Aktiv radarda tapılmadı")
    text = await radar_ai.explain(item, lang)
    return {"ready": text is not None, "text": text or ""}


@router.get(
    "/{key}/about",
    dependencies=[Depends(rate_limit("radar_ai", limit=20, window=60.0))],
)
async def radar_about(key: str, lang: str = Query("az")) -> StreamingResponse:
    """Aktiv haqqında icmalı seçilmiş dildə token-token axıdır (keşli).

    Keşli `find_item` (CoinGecko fetch kritik yolda deyil) + axın → açılış sürətli:
    istifadəçi ilk tokenləri ~1s-də görür, tam AI cavabını gözləmir.
    """
    lang = lang if lang in _LANGS else "az"
    item, _ = await radar.find_item(key)
    if item is None:
        raise HTTPException(status_code=404, detail="Aktiv radarda tapılmadı")

    async def gen():
        async for delta in radar_ai.about_stream(item, lang):
            yield delta

    return StreamingResponse(
        gen(),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{key}")
async def radar_detail(key: str) -> dict:
    """Aktiv detalı — info + açıqlama + sayt + opensource (GitHub) linki."""
    data = await radar.get_detail(key)
    if data is None:
        raise HTTPException(status_code=404, detail="Aktiv radarda tapılmadı")
    return data
