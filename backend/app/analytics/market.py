"""Canlı bazar qiymətləri — sabit, 7/24.

- Kripto (BTC, ETH): **Binance** public API — real-time, açarsız.
- Forex / indeks / əmtəə: **yfinance** (Yahoo) — tək sabit mənbə (keçid yox).

TradingView qəsdən istifadə OLUNMUR: rəsmi API yoxdur, scraping 429 ilə
bloklayır və qiymət mənbəyini "tərpədir" (qeyri-stabil). İki sabit mənbə +
keş = lent heç vaxt dayanmır.

Nəticə 60 saniyə keşlənir; xəta olarsa son uğurlu keş qaytarılır.
"""
from __future__ import annotations

import asyncio
import time

import httpx
import yfinance as yf

# Binance: real-time kripto.
_CRYPTO = [("BTC/USD", "BTCUSDT"), ("ETH/USD", "ETHUSDT")]

# yfinance: (ad, Yahoo simvolu, dəqiqlik).
_YF = [
    ("EUR/USD", "EURUSD=X", 4),
    ("DXY", "DX-Y.NYB", 2),
    ("S&P 500", "^GSPC", 0),
    ("NASDAQ", "^IXIC", 0),
    ("GBP/USD", "GBPUSD=X", 4),
    ("GOLD", "GC=F", 1),
    ("USD/JPY", "USDJPY=X", 2),
    ("WTI OIL", "CL=F", 2),
]

# Lentdə göstərilmə ardıcıllığı.
_ORDER = [
    "EUR/USD", "BTC/USD", "DXY", "S&P 500", "NASDAQ",
    "ETH/USD", "GBP/USD", "GOLD", "USD/JPY", "WTI OIL",
]

_TTL = 60.0
_cache: dict = {"ts": 0.0, "data": []}


def _fmt(value: float, dec: int) -> str:
    return f"{value:,.0f}" if dec == 0 else f"{value:,.{dec}f}"


def _quote(name: str, last: float, chg: float, dec: int) -> dict:
    return {
        "sym": name,
        "val": _fmt(last, dec),
        "chg": f"{chg:+.2f}%",
        "up": chg >= 0,
    }


async def _binance() -> dict[str, dict]:
    """Real-time kripto qiymət + 24s dəyişim."""
    syms = "[" + ",".join(f'"{s}"' for _, s in _CRYPTO) + "]"
    out: dict[str, dict] = {}
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbols": syms},
            )
            r.raise_for_status()
            by_sym = {row["symbol"]: row for row in r.json()}
        for name, sym in _CRYPTO:
            row = by_sym.get(sym)
            if row:
                out[name] = _quote(
                    name, float(row["lastPrice"]),
                    float(row["priceChangePercent"]), 0,
                )
    except (httpx.HTTPError, KeyError, ValueError):
        pass
    return out


def _yf_sync() -> dict[str, dict]:
    """Forex/indeks/əmtəə — son qiymət + dünənə görə dəyişim."""
    tickers = " ".join(s for _, s, _ in _YF)
    out: dict[str, dict] = {}
    try:
        df = yf.download(
            tickers, period="5d", interval="1d", progress=False, threads=True
        )["Close"]
    except Exception:  # noqa: BLE001
        return out
    for name, sym, dec in _YF:
        try:
            series = df[sym].dropna()
            last = float(series.iloc[-1])
            prev = float(series.iloc[-2])
            chg = (last - prev) / prev * 100 if prev else 0.0
            out[name] = _quote(name, last, chg, dec)
        except (KeyError, IndexError, ValueError, TypeError):
            continue
    return out


async def _fetch() -> list[dict]:
    crypto, yfin = await asyncio.gather(_binance(), asyncio.to_thread(_yf_sync))
    merged = {**yfin, **crypto}
    return [merged[name] for name in _ORDER if name in merged]


async def get_quotes() -> list[dict]:
    """Keşlənmiş canlı qiymətlər. Köhnəlibsə yenidən çəkir."""
    now = time.time()
    if _cache["data"] and now - _cache["ts"] < _TTL:
        return _cache["data"]
    data = await _fetch()
    if data:
        _cache["data"] = data
        _cache["ts"] = now
    return _cache["data"]


# ---- Metallar (Forex tab → "Metallar" kateqoriyası) ----
_METALS = [
    ("Gold", "GC=F", 1),
    ("Silver", "SI=F", 2),
    ("Platinum", "PL=F", 1),
    ("Palladium", "PA=F", 1),
    ("Copper", "HG=F", 3),
]
_metals_cache: dict = {"ts": 0.0, "data": []}


def _metals_sync() -> list[dict]:
    tickers = " ".join(s for _, s, _ in _METALS)
    out: list[dict] = []
    try:
        df = yf.download(
            tickers, period="1mo", interval="1d", progress=False, threads=True
        )["Close"]
    except Exception:  # noqa: BLE001
        return out
    for name, sym, dec in _METALS:
        try:
            series = df[sym].dropna()
            last = float(series.iloc[-1])
            prev = float(series.iloc[-2])
            chg = (last - prev) / prev * 100 if prev else 0.0
            q = _quote(name, last, chg, dec)
            q["spark"] = [round(float(v), 4) for v in series.iloc[-14:]]
            out.append(q)
        except (KeyError, IndexError, ValueError, TypeError):
            continue
    return out


async def get_metals() -> list[dict]:
    """Metal qiymətləri (Gold/Silver/Platinum/Palladium/Copper). 90s keş."""
    now = time.time()
    if _metals_cache["data"] and now - _metals_cache["ts"] < 90.0:
        return _metals_cache["data"]
    data = await asyncio.to_thread(_metals_sync)
    if data:
        _metals_cache["data"] = data
        _metals_cache["ts"] = now
    return _metals_cache["data"]


# ---- Əmtəələr (Commodities tab → qiymət + trend) ----
_COMMODITIES = [
    ("Uranium", "URA", 2),     # Global X Uranium ETF (uran proxy)
    ("WTI Oil", "CL=F", 2),
    ("Brent", "BZ=F", 2),
    ("Nat Gas", "NG=F", 3),
    ("Gasoline", "RB=F", 3),
    ("Wheat", "ZW=F", 1),
    ("Corn", "ZC=F", 1),
    ("Soybean", "ZS=F", 1),
    ("Coffee", "KC=F", 1),
    ("Sugar", "SB=F", 2),
]
_comm_cache: dict = {"ts": 0.0, "data": []}


def _commodities_sync() -> list[dict]:
    tickers = " ".join(s for _, s, _ in _COMMODITIES)
    out: list[dict] = []
    try:
        df = yf.download(
            tickers, period="1mo", interval="1d", progress=False, threads=True
        )["Close"]
    except Exception:  # noqa: BLE001
        return out
    for name, sym, dec in _COMMODITIES:
        try:
            series = df[sym].dropna()
            last = float(series.iloc[-1])
            prev = float(series.iloc[-2])
            chg = (last - prev) / prev * 100 if prev else 0.0
            q = _quote(name, last, chg, dec)
            q["spark"] = [round(float(v), 4) for v in series.iloc[-14:]]
            out.append(q)
        except (KeyError, IndexError, ValueError, TypeError):
            continue
    return out


async def get_commodities() -> list[dict]:
    """Əmtəə qiymətləri (uran, neft, qaz, taxıl və s.) + 14g trend. 90s keş."""
    now = time.time()
    if _comm_cache["data"] and now - _comm_cache["ts"] < 90.0:
        return _comm_cache["data"]
    data = await asyncio.to_thread(_commodities_sync)
    if data:
        _comm_cache["data"] = data
        _comm_cache["ts"] = now
    return _comm_cache["data"]
