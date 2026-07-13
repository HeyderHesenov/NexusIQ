"""Crypto Fear & Greed indeksi — alternative.me pulsuz API (açarsız).

Dəyər 0-100 + təsnifat. Nəticə 10 dəqiqə keşlənir (indeks gündə bir dəyişir).
"""
from __future__ import annotations

import httpx

from app.analytics import swr

_URL = "https://api.alternative.me/fng/?limit=1"
_TTL = 600.0
_cache: dict = {"ts": 0.0, "data": None}


async def _fetch() -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(_URL)
            r.raise_for_status()
            d = (r.json().get("data") or [])[0]
        return {
            "value": int(d["value"]),
            "label": str(d["value_classification"]),
            "updatedAt": int(d["timestamp"]),
        }
    except Exception:  # noqa: BLE001
        return None


async def get_fear_greed() -> dict | None:
    """{value:int, label:str, updatedAt:int} — SWR (stale-serve + coalesce)."""
    return await swr.get(_cache, _TTL, _fetch)
