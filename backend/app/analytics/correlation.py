"""Korrelyasiya analitikası — aktivlər arası Pearson korrelyasiyası.

Tarixi gündəlik qiymətlər yfinance (Yahoo) ilə çəkilir, gündəlik gəlirlər
(pct change) hesablanır, Pearson korrelyasiya matrisi qurulur.

Nəticə (window üzrə) keşlənir; yfinance xətası olarsa son uğurlu keş qaytarılır.
"""
from __future__ import annotations

import asyncio
import time

import pandas as pd
import yfinance as yf
from scipy.stats import pearsonr

from app.analytics import swr

# Korrelyasiya üçün aktiv kainatı: (key, göstəriş adı, Yahoo simvolu).
ASSETS: list[tuple[str, str, str]] = [
    ("btc", "BTC", "BTC-USD"),
    ("eth", "ETH", "ETH-USD"),
    ("spx", "S&P 500", "^GSPC"),
    ("ndx", "NASDAQ", "^NDX"),
    ("gold", "GOLD", "GC=F"),
    ("oil", "WTI OIL", "CL=F"),
    ("dxy", "DXY", "DX-Y.NYB"),
    ("eurusd", "EUR/USD", "EURUSD=X"),
    ("usdjpy", "USD/JPY", "USDJPY=X"),
]

_KEY_TO_SYM = {k: s for k, _, s in ASSETS}
_KEY_TO_LABEL = {k: lbl for k, lbl, _ in ASSETS}
_ALLOWED_WINDOWS = {30, 90, 180, 365}
_TTL = 1800.0  # 30 dəqiqə — tarixi data tez-tez dəyişmir.

_matrix_cache: dict[int, dict] = {}
_returns_cache: dict[int, tuple[float, pd.DataFrame]] = {}


def _yahoo_period(window_days: int) -> str:
    """yfinance period sətri — pəncərədən bir az artıq çəkirik (NaN buferi)."""
    if window_days <= 30:
        return "3mo"
    if window_days <= 90:
        return "6mo"
    if window_days <= 180:
        return "1y"
    return "2y"


def _fetch_returns(window_days: int) -> pd.DataFrame:
    """Bütün aktivlərin gündəlik gəlir DataFrame-i (NaN-lar atılmış)."""
    syms = [s for _, _, s in ASSETS]
    raw = yf.download(
        syms,
        period=_yahoo_period(window_days),
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    close = close.reindex(columns=syms)
    # Son `window_days` ticarət gününü saxla.
    close = close.tail(window_days + 5)
    returns = close.pct_change().dropna(how="all")
    # Simvol → key adlandırması.
    sym_to_key = {s: k for k, _, s in ASSETS}
    returns = returns.rename(columns=sym_to_key)
    return returns


async def _get_returns(window_days: int) -> pd.DataFrame:
    """Keşli gəlir matrisi (thread-də yfinance çağırışı)."""
    cached = _returns_cache.get(window_days)
    now = time.time()
    if cached and now - cached[0] < _TTL:
        return cached[1]
    df = await asyncio.to_thread(_fetch_returns, window_days)
    if not df.empty:
        _returns_cache[window_days] = (now, df)
    elif cached:
        return cached[1]
    return df


def _norm_window(window_days: int) -> int:
    return window_days if window_days in _ALLOWED_WINDOWS else 90


async def get_matrix(window_days: int = 90) -> dict:
    """Pearson korrelyasiya matrisi (SWR — heç vaxt bloklamaz, köhnəni qaytarar)."""
    window_days = _norm_window(window_days)
    store = _matrix_cache.setdefault(window_days, {"ts": 0.0, "data": None})
    data = await swr.get(store, _TTL, lambda: _build_matrix(window_days))
    if data:
        return data
    assets_meta = [{"key": k, "label": lbl, "sym": s} for k, lbl, s in ASSETS]
    return {"window": window_days, "assets": assets_meta, "matrix": []}


async def _build_matrix(window_days: int) -> dict | None:
    """Matrisi hesabla. yfinance boş qaytararsa None (köhnə keş qorunur)."""
    returns = await _get_returns(window_days)
    if returns.empty:
        return None

    keys = [k for k, _, _ in ASSETS if k in returns.columns]
    corr = returns[keys].corr(method="pearson")
    order = [k for k, _, _ in ASSETS]
    matrix: list[list[float | None]] = []
    for r in order:
        row: list[float | None] = []
        for c in order:
            if r in corr.index and c in corr.columns:
                v = corr.at[r, c]
                row.append(None if pd.isna(v) else round(float(v), 2))
            else:
                row.append(None)
        matrix.append(row)

    assets_meta = [{"key": k, "label": lbl, "sym": s} for k, lbl, s in ASSETS]
    return {"window": window_days, "assets": assets_meta, "matrix": matrix}


async def get_pair(key_a: str, key_b: str, window_days: int = 90) -> dict | None:
    """İki aktiv: Pearson dəyəri + normallaşdırılmış qiymət seriyaları (chart).

    Normallaşma: hər seriya başlanğıcdan 100-ə nisbətdə (müqayisə üçün).
    """
    window_days = _norm_window(window_days)
    if key_a not in _KEY_TO_SYM or key_b not in _KEY_TO_SYM or key_a == key_b:
        return None

    returns = await _get_returns(window_days)
    if returns.empty or key_a not in returns.columns or key_b not in returns.columns:
        return None

    pair = returns[[key_a, key_b]].dropna()
    if len(pair) < 3:
        return None

    value, _ = pearsonr(pair[key_a].to_numpy(), pair[key_b].to_numpy())

    # Gəlirlərdən kumulyativ indeks (başlanğıc = 100) — normallaşmış seriya.
    idx_a = 100.0 * (1.0 + pair[key_a]).cumprod()
    idx_b = 100.0 * (1.0 + pair[key_b]).cumprod()
    series = [
        {
            "date": d.strftime("%Y-%m-%d"),
            "a": round(float(a), 2),
            "b": round(float(b), 2),
        }
        for d, a, b in zip(pair.index, idx_a, idx_b)
    ]

    return {
        "a": {"key": key_a, "label": _KEY_TO_LABEL[key_a]},
        "b": {"key": key_b, "label": _KEY_TO_LABEL[key_b]},
        "window": window_days,
        "value": round(float(value), 3),
        "series": series,
    }


def label_for(key: str) -> str:
    return _KEY_TO_LABEL.get(key, key)


# Sərbəst mətndə aktiv adlarını tanımaq üçün ləqəblər (4 dil + simvollar).
_ALIASES: dict[str, list[str]] = {
    "btc": ["btc", "bitcoin", "биткоин", "bitkoin"],
    "eth": ["eth", "ethereum", "ether", "эфир"],
    "spx": ["s&p 500", "s&p500", "s&p", "sp500", "spx", "snp"],
    "ndx": ["nasdaq", "ndx"],
    "gold": ["gold", "qızıl", "qizil", "altın", "altin", "xau", "золото"],
    "oil": ["wti oil", "wti", "crude", "oil", "neft", "petrol", "нефть"],
    "dxy": ["dxy", "dollar index", "dollar indeksi", "индекс доллара"],
    "eurusd": ["eur/usd", "eurusd", "eur usd", "eur-usd", "euro", "avro", "евро"],
    "usdjpy": ["usd/jpy", "usdjpy", "usd jpy", "usd-jpy", "yen", "jpy", "иена", "yeni"],
}


def detect_assets(text: str) -> list[str]:
    """Mətndə tanınan aktiv açarlarını görünmə sırası ilə qaytarır (0+)."""
    low = f" {text.lower()} "
    hits: list[tuple[int, str]] = []
    for key, aliases in _ALIASES.items():
        pos = min(
            (low.find(a) for a in aliases if low.find(a) >= 0),
            default=-1,
        )
        if pos >= 0:
            hits.append((pos, key))
    hits.sort()
    return [k for _, k in hits]


def detect_pair(text: str) -> tuple[str, str] | None:
    """Mətndə iki aktiv adı tapıb (görünmə sırası ilə) açar cütü qaytarır.

    Məs. "EUR/USD vs DXY əlaqəsi" → ("eurusd", "dxy"). Tapılmasa None.
    """
    keys = detect_assets(text)
    if len(keys) >= 2:
        return keys[0], keys[1]
    return None
