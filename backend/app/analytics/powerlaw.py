"""Power Law (Güc Qanunu) modeli — BTC üçün uzunmüddətli ədalətli dəyər.

log10(qiymət) = a + b·log10(genesis-dən günlər), t0 = genesis (2009-01-03).
Əmsallar HARDCODE edilmir — BTC-nin tam tarixindən reqressiya ilə fit edilir
(b ≈ 5-6, R² ≈ 0.92).

QEYD: Power law praktikada yalnız BTC üçün etibarlı işləyir. Digər coinlərdə
qanun tutmur, forex (mean-reverting) və əmtəələr isə tamamilə uyğun deyil —
ona görə yalnız BTC saxlanılır.
"""
from __future__ import annotations

import asyncio
from datetime import date, timedelta

import numpy as np
import yfinance as yf

from app.analytics import swr

# key → (label, Yahoo simvolu). Power law yalnız BTC üçün etibarlı işləyir
# (R² ~0.92, genesis 2009-dan eksponensial trend). Digər coinlərdə qanun
# tutmur — ona görə yalnız BTC saxlanılır.
ASSETS: dict[str, tuple[str, str]] = {
    "btc": ("BTC", "BTC-USD"),
}
_BTC_GENESIS = date(2009, 1, 3)

# Per-key SWR store: key → {"ts","data"} (stale-serve + lock coalescing).
_stores: dict[str, dict] = {}
_TTL = 6 * 3600.0


def list_powerlaw_assets() -> list[dict]:
    return [{"key": k, "label": lbl} for k, (lbl, _) in ASSETS.items()]


def _fit_sync(key: str) -> dict | None:
    meta = ASSETS.get(key)
    if not meta:
        return None
    label, sym = meta

    df = yf.download(
        sym, period="max", interval="1d",
        auto_adjust=True, progress=False, threads=True,
    )["Close"]
    series = df.dropna()
    if hasattr(series, "ndim") and series.ndim > 1:
        series = series.iloc[:, 0]
    if len(series) < 400:
        return None

    dates = [d.date() if hasattr(d, "date") else d for d in series.index]
    # t0: BTC üçün genesis, digərləri üçün ilk data günü.
    t0 = _BTC_GENESIS if key == "btc" else dates[0] - timedelta(days=1)

    days = np.array([(d - t0).days for d in dates], dtype=float)
    prices = series.to_numpy(dtype=float)
    mask = (days > 0) & (prices > 0)
    days, prices = days[mask], prices[mask]
    dates = [d for d, m in zip(dates, mask) if m]

    x = np.log10(days)
    y = np.log10(prices)
    b, a = np.polyfit(x, y, 1)

    yhat = a + b * x
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0

    resid = y - yhat
    off_low = float(np.percentile(resid, 2))
    off_high = float(np.percentile(resid, 98))

    def model_for(d: int) -> float:
        return float(10 ** (a + b * np.log10(d)))

    last_date = dates[-1]
    last_days = (last_date - t0).days
    last_price = float(prices[-1])
    model_now = model_for(last_days)

    series_out = []
    step = max(1, len(dates) // 200)
    for i in range(0, len(dates), step):
        d = dates[i]
        m = model_for((d - t0).days)
        series_out.append({
            "date": d.strftime("%Y-%m-%d"),
            "actual": round(float(prices[i]), 4),
            "model": round(m, 4),
            "low": round(m * 10 ** off_low, 4),
            "high": round(m * 10 ** off_high, 4),
        })

    projections = []
    for years in (1, 2, 4, 8, 10, 20):
        fd = last_date + timedelta(days=365 * years)
        m = model_for((fd - t0).days)
        projections.append({
            "years": years,
            "date": fd.strftime("%Y-%m-%d"),
            "model": round(m, 4),
            "support": round(m * 10 ** off_low, 4),
            "resistance": round(m * 10 ** off_high, 4),
        })

    return {
        "key": key,
        "label": label,
        "a": round(a, 4),
        "b": round(b, 4),
        "r2": round(r2, 4),
        "genesis": t0.strftime("%Y-%m-%d"),
        "lastDate": last_date.strftime("%Y-%m-%d"),
        "price": round(last_price, 4),
        "model": round(model_now, 4),
        "support": round(model_now * 10 ** off_low, 4),
        "resistance": round(model_now * 10 ** off_high, 4),
        "deviationPct": round((last_price / model_now - 1) * 100, 1),
        "projections": projections,
        "series": series_out,
    }


async def get_power_law(key: str = "btc") -> dict | None:
    """Seçilmiş coinin power-law modeli — SWR (stale-serve + coalesce, 6 saat).

    Fit ağırdır (period=max yükləmə + polyfit, bir neçə saniyə) — SWR köhnə
    dəyəri dərhal verir, fonda yeniləyir; soyuq sorğular tək fit-də birləşir.
    """
    key = key if key in ASSETS else "btc"
    store = _stores.setdefault(key, {"ts": 0.0, "data": None})
    return await swr.get(store, _TTL, lambda: asyncio.to_thread(_fit_sync, key))
