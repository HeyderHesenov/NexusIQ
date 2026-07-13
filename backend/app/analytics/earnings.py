"""US səhm gəlir (earnings) təqvimi — yfinance ilə yaxın hesabat tarixləri.

Hər iri şirkət üçün ən yaxın GƏLƏCƏK earnings tarixi. 6 saat keşlənir
(tarixlər tez-tez dəyişmir). yfinance sinxron → thread-də paralel çağırılır.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import yfinance as yf

from app.analytics import swr

# (ticker, şirkət adı, AI-səhmidirmi) — iri kapitallı US şirkətləri.
# ai=True → "AI Səhmləri" kateqoriyasında da görünür.
_TICKERS = [
    ("AAPL", "Apple", False),
    ("MSFT", "Microsoft", True),
    ("NVDA", "NVIDIA", True),
    ("AMZN", "Amazon", False),
    ("GOOGL", "Alphabet", True),
    ("META", "Meta", True),
    ("TSLA", "Tesla", False),
    ("JPM", "JPMorgan", False),
    ("V", "Visa", False),
    ("WMT", "Walmart", False),
    ("XOM", "Exxon Mobil", False),
    ("NFLX", "Netflix", False),
    ("AMD", "AMD", True),
    ("KO", "Coca-Cola", False),
    ("DIS", "Disney", False),
    # AI-yönümlü əlavələr
    ("AVGO", "Broadcom", True),
    ("MU", "Micron", True),
    ("SMCI", "Super Micro", True),
    ("ARM", "Arm Holdings", True),
    ("TSM", "TSMC", True),
    ("PLTR", "Palantir", True),
]

_TTL = 21600.0  # 6 saat
# SWR: köhnə dəyəri dərhal ver, fonda yenilə; soyuq sorğular lock ilə birləşir —
# yoxsa hər soyuq çağırış 21 paralel yfinance thread açıb pool-u boğur.
_cache: dict = {"ts": 0.0, "data": None}


def _next_earning(sym: str, name: str, ai: bool) -> dict | None:
    """Bu ticker üçün ən yaxın gələcək earnings tarixi (yoxdursa None)."""
    try:
        df = yf.Ticker(sym).get_earnings_dates(limit=8)
        if df is None or df.empty:
            return None
        now = datetime.now(timezone.utc)
        future = [ts for ts in df.index.to_pydatetime() if ts.astimezone(timezone.utc) >= now]
        if not future:
            return None
        ts = min(future)
        return {
            "sym": sym,
            "name": name,
            "date": ts.date().isoformat(),
            "time": ts.strftime("%H:%M"),
            "ai": ai,
        }
    except Exception:  # noqa: BLE001
        return None


async def _fetch_earnings() -> list[dict]:
    try:
        results = await asyncio.gather(
            *(asyncio.to_thread(_next_earning, s, n, ai) for s, n, ai in _TICKERS)
        )
    except Exception:  # noqa: BLE001
        return []
    return sorted((r for r in results if r), key=lambda x: x["date"])


async def get_earnings() -> list[dict]:
    """Yaxın earnings hesabatları, tarixə görə sıralı. SWR (stale-serve+coalesce)."""
    return await swr.get(_cache, _TTL, _fetch_earnings) or []
