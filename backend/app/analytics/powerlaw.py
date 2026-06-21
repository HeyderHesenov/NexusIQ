"""Power Law (Güc Qanunu) modeli — lider coinlər üçün uzunmüddətli ədalətli dəyər.

log10(qiymət) = a + b·log10(t0-dan günlər). BTC üçün t0 = genesis (2009-01-03);
digər coinlər üçün t0 = ilk ticarət günü. Əmsallar HARDCODE edilmir — hər aktiv
öz tam tarixindən reqressiya ilə fit edilir (b ≈ 5-6, R² yüksək).

QEYD: Power law yalnız uzunmüddətli eksponensial böyüyən şəbəkə aktivləri (kripto)
üçün məntiqlidir. Forex (mean-reverting) və əmtəələr daxil EDİLMİR.
"""
from __future__ import annotations

import asyncio
import time
from datetime import date, timedelta

import numpy as np
import yfinance as yf

# key → (label, Yahoo simvolu). Yalnız lider coinlər.
ASSETS: dict[str, tuple[str, str]] = {
    "btc": ("BTC", "BTC-USD"),
    "eth": ("ETH", "ETH-USD"),
    "bnb": ("BNB", "BNB-USD"),
    "sol": ("SOL", "SOL-USD"),
    "xrp": ("XRP", "XRP-USD"),
    "doge": ("DOGE", "DOGE-USD"),
    "hype": ("HYPE", "HYPE32196-USD"),
    "link": ("LINK", "LINK-USD"),
    "ltc": ("LTC", "LTC-USD"),
    "trx": ("TRX", "TRX-USD"),
}
_BTC_GENESIS = date(2009, 1, 3)

_cache: dict[str, dict] = {}
_cache_ts: dict[str, float] = {}
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
    for years in (1, 2, 4):
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
    """Seçilmiş coinin power-law modeli (6 saat keş)."""
    key = key if key in ASSETS else "btc"
    now = time.time()
    if _cache.get(key) and now - _cache_ts.get(key, 0) < _TTL:
        return _cache[key]
    data = await asyncio.to_thread(_fit_sync, key)
    if data:
        _cache[key] = data
        _cache_ts[key] = now
    return _cache.get(key)
