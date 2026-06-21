"""Aktiv reyestri + canlı qiymət/tarixçə — watchlist, asset səhifəsi, müqayisə.

Tək mənbə: yfinance. Qiymət fast_info (canlı), tarixçə isə gündəlik bağlanış.
Nəticələr keşlənir.
"""
from __future__ import annotations

import asyncio
import time

import httpx
import yfinance as yf

from app.analytics.market import _live_last_prev

# (key, label, Yahoo simvolu, tip, dəqiqlik)
ASSETS: list[tuple[str, str, str, str, int]] = [
    ("btc", "BTC", "BTC-USD", "crypto", 0),
    ("eth", "ETH", "ETH-USD", "crypto", 0),
    ("sol", "SOL", "SOL-USD", "crypto", 2),
    ("xrp", "XRP", "XRP-USD", "crypto", 3),
    # İndekslər (12)
    ("spx", "S&P 500", "^GSPC", "index", 0),
    ("ndx", "NASDAQ", "^NDX", "index", 0),
    ("dji", "Dow Jones", "^DJI", "index", 0),
    ("rut", "Russell 2000", "^RUT", "index", 0),
    ("vix", "VIX", "^VIX", "index", 2),
    ("ftse", "FTSE 100", "^FTSE", "index", 0),
    ("dax", "DAX", "^GDAXI", "index", 0),
    ("cac", "CAC 40", "^FCHI", "index", 0),
    ("nikkei", "Nikkei 225", "^N225", "index", 0),
    ("hsi", "Hang Seng", "^HSI", "index", 0),
    ("stoxx", "Euro Stoxx 50", "^STOXX50E", "index", 0),
    ("tsx", "TSX", "^GSPTSE", "index", 0),
    # Forex (4)
    ("eurusd", "EUR/USD", "EURUSD=X", "forex", 4),
    ("gbpusd", "GBP/USD", "GBPUSD=X", "forex", 4),
    ("usdjpy", "USD/JPY", "USDJPY=X", "forex", 2),
    ("dxy", "DXY", "DX-Y.NYB", "forex", 2),
    # Əmtəələr (3)
    ("oil", "WTI Oil", "CL=F", "commodity", 2),
    ("brent", "Brent", "BZ=F", "commodity", 2),
    ("natgas", "Nat Gas", "NG=F", "commodity", 3),
    # Metallar (10)
    ("gold", "Gold", "GC=F", "metal", 1),
    ("silver", "Silver", "SI=F", "metal", 2),
    ("platinum", "Platinum", "PL=F", "metal", 1),
    ("palladium", "Palladium", "PA=F", "metal", 1),
    ("copper", "Copper", "HG=F", "metal", 3),
    ("aluminum", "Aluminum", "ALI=F", "metal", 1),
    ("lithium", "Lithium", "LIT", "metal", 2),
    ("uranium", "Uranium", "URA", "metal", 2),
    ("steel", "Steel", "SLX", "metal", 2),
    ("rareearth", "Rare Earth", "REMX", "metal", 2),
]

_BY_KEY = {k: (k, lbl, sym, typ, dec) for k, lbl, sym, typ, dec in ASSETS}

_RANGE_MAP = {
    "1mo": ("1mo", "1d"),
    "3mo": ("3mo", "1d"),
    "6mo": ("6mo", "1d"),
    "1y": ("1y", "1d"),
}

_quote_cache: dict[str, tuple[float, dict]] = {}
_hist_cache: dict[str, tuple[float, dict]] = {}
_QUOTE_TTL = 60.0
_HIST_TTL = 1800.0

# ---- Binance top coinlər (dinamik) ----
# Reyestrdə onsuz da olan baza coinlər (dublikat olmasın).
_REGISTRY_BASES = {"BTC", "ETH", "SOL", "XRP"}
# Stablecoin / leveraged token — atlanır.
_SKIP_BASES = {"USDT", "USDC", "FDUSD", "TUSD", "BUSD", "DAI", "USDP", "EUR", "USDE"}
_TOP_COINS = 50
_COINS_TTL = 300.0  # 5 dəqiqə
# key → {label, symbol, price, chgPct}
_coins: dict[str, dict] = {}
_coins_ts = 0.0


def _is_leveraged(base: str) -> bool:
    return any(base.endswith(x) for x in ("UP", "DOWN", "BULL", "BEAR"))


async def _ensure_coins() -> None:
    """Binance-dən həcmə görə top coinləri çəkir (5 dəq keş)."""
    global _coins, _coins_ts
    now = time.time()
    if _coins and now - _coins_ts < _COINS_TTL:
        return
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get("https://api.binance.com/api/v3/ticker/24hr")
            r.raise_for_status()
            rows = r.json()
    except (httpx.HTTPError, ValueError):
        return  # köhnə keş qalır

    usdt = [
        row for row in rows
        if row.get("symbol", "").endswith("USDT")
    ]
    usdt.sort(key=lambda x: float(x.get("quoteVolume", 0) or 0), reverse=True)

    coins: dict[str, dict] = {}
    for row in usdt:
        sym = row["symbol"]
        base = sym[:-4]  # "USDT" çıxar
        if (
            base in _REGISTRY_BASES
            or base in _SKIP_BASES
            or "USD" in base  # stablecoin variantları (USD1, USDE, ...)
            or _is_leveraged(base)
        ):
            continue
        key = f"c_{base.lower()}"
        coins[key] = {
            "label": base,
            "symbol": sym,
            "price": float(row.get("lastPrice", 0) or 0),
            "chgPct": float(row.get("priceChangePercent", 0) or 0),
        }
        if len(coins) >= _TOP_COINS:
            break

    if coins:
        _coins = coins
        _coins_ts = now


async def list_assets() -> list[dict]:
    """Reyestr metadatası (UI seçicilər üçün) + Binance top coinlər."""
    await _ensure_coins()
    base = [
        {"key": k, "label": lbl, "sym": sym, "type": typ}
        for k, lbl, sym, typ, _ in ASSETS
    ]
    coins = [
        {"key": k, "label": v["label"], "sym": v["symbol"], "type": "crypto"}
        for k, v in _coins.items()
    ]
    return base + coins


def _coin_dec(price: float) -> int:
    if price >= 1000:
        return 0
    if price >= 1:
        return 2
    if price >= 0.01:
        return 4
    return 6


def _fmt(value: float, dec: int) -> str:
    return f"{value:,.0f}" if dec == 0 else f"{value:,.{dec}f}"


def _quote_sync(key: str) -> dict | None:
    meta = _BY_KEY.get(key)
    if not meta:
        return None
    _, label, sym, typ, dec = meta
    lp = _live_last_prev(sym)
    if lp is None:
        return None
    last, prev = lp
    chg = (last - prev) / prev * 100 if prev else 0.0
    return {
        "key": key,
        "label": label,
        "type": typ,
        "val": _fmt(last, dec),
        "price": round(last, max(dec, 2)),
        "chg": f"{chg:+.2f}%",
        "chgPct": round(chg, 2),
        "up": chg >= 0,
    }


async def get_quote(key: str) -> dict | None:
    """Tək aktivin canlı qiyməti (60s keş)."""
    if key.startswith("c_"):
        await _ensure_coins()
        c = _coins.get(key)
        if not c:
            return None
        last, chg = c["price"], c["chgPct"]
        dec = _coin_dec(last)
        return {
            "key": key,
            "label": c["label"],
            "type": "crypto",
            "val": _fmt(last, dec),
            "price": last,
            "chg": f"{chg:+.2f}%",
            "chgPct": round(chg, 2),
            "up": chg >= 0,
        }

    now = time.time()
    cached = _quote_cache.get(key)
    if cached and now - cached[0] < _QUOTE_TTL:
        return cached[1]
    data = await asyncio.to_thread(_quote_sync, key)
    if data:
        _quote_cache[key] = (now, data)
    return data


_KLINE_LIMITS = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365}


async def _coin_history(key: str, rng: str) -> dict | None:
    c = _coins.get(key)
    if not c:
        return None
    limit = _KLINE_LIMITS.get(rng, 90)
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            r = await client.get(
                "https://api.binance.com/api/v3/klines",
                params={"symbol": c["symbol"], "interval": "1d", "limit": limit},
            )
            r.raise_for_status()
            rows = r.json()
    except (httpx.HTTPError, ValueError):
        return None
    dec = _coin_dec(c["price"])
    points = []
    for k in rows:
        ts = int(k[0]) // 1000
        from datetime import datetime, timezone

        d = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        points.append({"date": d, "close": round(float(k[4]), max(dec, 2))})
    if len(points) < 2:
        return None
    first, last = points[0]["close"], points[-1]["close"]
    chg = (last - first) / first * 100 if first else 0.0
    return {
        "key": key,
        "label": c["label"],
        "type": "crypto",
        "range": rng,
        "points": points,
        "changePct": round(chg, 2),
    }


def _history_sync(key: str, rng: str) -> dict | None:
    meta = _BY_KEY.get(key)
    if not meta:
        return None
    _, label, sym, typ, dec = meta
    period, interval = _RANGE_MAP.get(rng, _RANGE_MAP["3mo"])
    try:
        df = yf.download(
            sym, period=period, interval=interval,
            auto_adjust=True, progress=False, threads=True,
        )["Close"]
    except Exception:  # noqa: BLE001
        return None
    series = df.dropna()
    if hasattr(series, "iloc") and getattr(series, "ndim", 1) > 1:
        series = series.iloc[:, 0]
    points = [
        {"date": d.strftime("%Y-%m-%d"), "close": round(float(v), max(dec, 2))}
        for d, v in series.items()
    ]
    if len(points) < 2:
        return None
    first = points[0]["close"]
    last = points[-1]["close"]
    chg = (last - first) / first * 100 if first else 0.0
    return {
        "key": key,
        "label": label,
        "type": typ,
        "range": rng,
        "points": points,
        "changePct": round(chg, 2),
    }


_overview_cache: dict = {"ts": 0.0, "data": []}
_OVERVIEW_TTL = 600.0  # 10 dəqiqə


def _registry_overview_sync() -> dict[str, dict]:
    """Reyestr aktivləri — toplu qiymət + 1aylıq sparkline (tək yf çağırışı)."""
    out: dict[str, dict] = {}
    syms = [s for _, _, s, _, _ in ASSETS]
    try:
        df = yf.download(
            " ".join(syms), period="1mo", interval="1d",
            auto_adjust=True, progress=False, threads=True,
        )["Close"]
    except Exception:  # noqa: BLE001
        return out
    for key, label, sym, typ, dec in ASSETS:
        try:
            series = df[sym].dropna() if sym in df else df.dropna()
            closes = [float(v) for v in series.tail(22)]
            if len(closes) < 2:
                continue
            last, prev = closes[-1], closes[-2]
            chg = (last - prev) / prev * 100 if prev else 0.0
            out[key] = {
                "key": key, "label": label, "type": typ,
                "val": _fmt(last, dec), "price": last,
                "chg": f"{chg:+.2f}%", "chgPct": round(chg, 2), "up": chg >= 0,
                "spark": [round(c, 4) for c in closes],
            }
        except (KeyError, IndexError, ValueError, TypeError):
            continue
    return out


async def _coin_spark(symbol: str) -> list[float]:
    """Bir coin üçün ~7 günlük sparkline (Binance klines, 6 saatlıq)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.binance.com/api/v3/klines",
                params={"symbol": symbol, "interval": "6h", "limit": 28},
            )
            r.raise_for_status()
            return [round(float(k[4]), 6) for k in r.json()]
    except (httpx.HTTPError, ValueError, IndexError):
        return []


_news_cache: dict[str, tuple[float, list]] = {}
_NEWS_TTL = 1800.0  # 30 dəqiqə


def _yahoo_sym_for(key: str) -> str | None:
    if key.startswith("c_"):
        c = _coins.get(key)
        return f"{c['label']}-USD" if c else None
    meta = _BY_KEY.get(key)
    return meta[2] if meta else None


def _news_sync(sym: str) -> list[dict]:
    """Yahoo Finance-in həmin ticker üçün xəbərləri."""
    try:
        raw = yf.Ticker(sym).news or []
    except Exception:  # noqa: BLE001
        return []
    out: list[dict] = []
    for item in raw:
        c = item.get("content") or item
        if not isinstance(c, dict):
            continue
        title = c.get("title")
        if not title:
            continue
        url = None
        for f in ("clickThroughUrl", "canonicalUrl"):
            v = c.get(f)
            if isinstance(v, dict) and v.get("url"):
                url = v["url"]
                break
        url = url or c.get("link")
        prov = c.get("provider")
        source = prov.get("displayName") if isinstance(prov, dict) else None
        th = c.get("thumbnail")
        image = th.get("originalUrl") if isinstance(th, dict) else None
        out.append({
            "title": title,
            "url": url,
            "source": source,
            "publishedAt": c.get("pubDate") or c.get("displayTime"),
            "image": image,
            "summary": c.get("summary") or c.get("description"),
        })
    return out


async def get_asset_news(key: str) -> list[dict]:
    """Aktivə aid xəbərlər (Yahoo Finance ticker xəbərləri, 30 dəq keş)."""
    now = time.time()
    cached = _news_cache.get(key)
    if cached and now - cached[0] < _NEWS_TTL:
        return cached[1]
    if key.startswith("c_"):
        await _ensure_coins()
    sym = _yahoo_sym_for(key)
    if not sym:
        return []
    data = await asyncio.to_thread(_news_sync, sym)
    if data:
        _news_cache[key] = (now, data)
    return data


async def get_overview() -> list[dict]:
    """Bütün aktivlər — qiymət + 24s dəyişim + sparkline (CMC tərzi cədvəl, 10 dəq keş)."""
    now = time.time()
    if _overview_cache["data"] and now - _overview_cache["ts"] < _OVERVIEW_TTL:
        return _overview_cache["data"]

    await _ensure_coins()
    reg = await asyncio.to_thread(_registry_overview_sync)

    # Coin sparkline-ları paralel (məhdud).
    coin_items = list(_coins.items())
    sem = asyncio.Semaphore(8)

    async def coin_row(key: str, c: dict) -> dict:
        async with sem:
            spark = await _coin_spark(c["symbol"])
        dec = _coin_dec(c["price"])
        return {
            "key": key, "label": c["label"], "type": "crypto",
            "val": _fmt(c["price"], dec), "price": c["price"],
            "chg": f"{c['chgPct']:+.2f}%", "chgPct": round(c["chgPct"], 2),
            "up": c["chgPct"] >= 0, "spark": spark,
        }

    coin_rows = await asyncio.gather(*(coin_row(k, c) for k, c in coin_items))

    # Sıra: reyestr (ASSETS ardıcıllığı) + coinlər (həcm sırası).
    rows = [reg[k] for k, _, _, _, _ in ASSETS if k in reg] + list(coin_rows)
    if rows:
        _overview_cache["data"] = rows
        _overview_cache["ts"] = now
    return _overview_cache["data"]


async def get_history(key: str, rng: str = "3mo") -> dict | None:
    """Aktivin tarixi qiymət seriyası (30 dəq keş)."""
    rng = rng if rng in _RANGE_MAP else "3mo"
    ck = f"{key}:{rng}"
    now = time.time()
    cached = _hist_cache.get(ck)
    if cached and now - cached[0] < _HIST_TTL:
        return cached[1]

    if key.startswith("c_"):
        await _ensure_coins()
        data = await _coin_history(key, rng)
    else:
        data = await asyncio.to_thread(_history_sync, key, rng)

    if data:
        _hist_cache[ck] = (now, data)
    return data
