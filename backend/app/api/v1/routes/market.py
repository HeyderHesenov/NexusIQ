"""Bazar lenti route-u — canlı qiymətlər."""
from __future__ import annotations

from fastapi import APIRouter

from fastapi import Query

from app.agents.event_ai import event_brief
from app.agents.llm import has_openai
from app.analytics.calendar import get_calendar
from app.analytics.crypto_calendar import get_crypto_calendar
from app.analytics.earnings import get_earnings
from app.analytics.majors_calendar import get_majors_calendar
from app.analytics.feargreed import get_fear_greed
from app.analytics.market import get_commodities, get_metals, get_quotes

router = APIRouter()


@router.get("/ticker")
async def ticker() -> list[dict]:
    """Lent üçün canlı qiymətlər (keşlənmiş)."""
    return await get_quotes()


@router.get("/feargreed")
async def feargreed() -> dict | None:
    """Crypto Fear & Greed indeksi (keşlənmiş)."""
    return await get_fear_greed()


@router.get("/calendar")
async def calendar() -> list[dict]:
    """Bu həftənin iqtisadi təqvimi — ForexFactory pulsuz XML."""
    return await get_calendar()


@router.get("/crypto-calendar")
async def crypto_calendar() -> list[dict]:
    """Crypto təqvimi — sektor etiketli token unlock-ları (major/rwa/ai)."""
    return await get_crypto_calendar()


@router.get("/majors-calendar")
async def majors_calendar() -> list[dict]:
    """Lider coinlər təqvimi — BTC halving, XRP escrow, BNB burn, unlock-lar."""
    return await get_majors_calendar()


@router.get("/earnings")
async def earnings() -> list[dict]:
    """US səhm gəlir hesabatları (hər biri `ai` etiketi ilə)."""
    return await get_earnings()


@router.get("/metals")
async def metals() -> list[dict]:
    """Metal qiymətləri — Forex tab "Metallar" kateqoriyası."""
    return await get_metals()


@router.get("/commodities")
async def commodities() -> list[dict]:
    """Əmtəə qiymətləri — Commodities tab (uran, neft, taxıl və s.)."""
    return await get_commodities()


_LANGS = {"az", "en", "ru", "tr"}


@router.get("/event-brief")
async def event_brief_route(
    title: str = Query(..., min_length=1),
    country: str = Query(""),
    impact: str = Query(""),
    lang: str = Query("az"),
) -> dict:
    """Təqvim hadisəsi haqqında AI izahı — nədir, yuxarı/aşağı təsir, pairlər."""
    lang = lang if lang in _LANGS else "az"
    if not has_openai():
        return {"ready": False}
    brief = await event_brief(title, country, impact, lang)
    if not brief:
        return {"ready": False}
    return {"ready": True, **brief}
