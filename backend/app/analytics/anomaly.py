"""Anomaliya aşkarlama — qiymət + həcm sıçrayışları (PULSUZ).

Mövcud yfinance datası üzərində sırf hesablama. API xərci yoxdur.

Metod — **robust Z-score** (median + MAD), fat-tail davamlı:
  z = 0.6745 * (x - median) / MAD
MAD = 0 olarsa std-ə fallback; std də 0 olarsa siqnal yox.

Anomaliya = |price_z| >= 3 VƏ volume_z >= 2 (həcm təsdiqi).
Şiddət: 3–4 orta, 4–5 yüksək, >=5 ekstremal.

Həcmi olmayan aktivlər (forex =X, DXY) təbii şəkildə kənarda qalır.
"""
from __future__ import annotations

import asyncio
import math
import time

import yfinance as yf

from app.analytics.assets import ASSETS

_MAD_SCALE = 0.6745
_PRICE_Z = 3.0
_VOLUME_Z = 2.0
_WINDOW = 90  # gündəlik nöqtə

_TTL = 300.0  # 5 dəqiqə keş
_cache: dict = {"ts": 0.0, "data": []}


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    m = n // 2
    return s[m] if n % 2 else (s[m - 1] + s[m]) / 2.0


def robust_z(values: list[float]) -> float | None:
    """Sonuncu nöqtənin robust z-balı (median + MAD, std fallback).

    None — seriya çox qısa və ya dağılım sıfırdırsa (siqnal yox).
    """
    if not values or len(values) < 5:
        return None
    last = values[-1]
    med = _median(values)
    mad = _median([abs(v - med) for v in values])
    if mad > 0:
        return _MAD_SCALE * (last - med) / mad
    # Fallback: klassik std.
    n = len(values)
    mean = sum(values) / n
    std = math.sqrt(sum((v - mean) ** 2 for v in values) / n)
    if std > 0:
        return (last - mean) / std
    return None


def _severity(price_z: float) -> str:
    a = abs(price_z)
    if a >= 5:
        return "extreme"
    if a >= 4:
        return "high"
    return "medium"


def _evaluate(key: str, label: str, typ: str, closes: list[float],
              volumes: list[float], asof: str) -> dict | None:
    """Bir aktivin son nöqtəsini yoxla — anomaliya varsa obyekt qaytar."""
    if len(closes) < 30:
        return None
    returns = [closes[i] / closes[i - 1] - 1.0
               for i in range(1, len(closes)) if closes[i - 1]]
    price_z = robust_z(returns[-_WINDOW:])
    volume_z = robust_z(volumes[-_WINDOW:]) if volumes else None
    if price_z is None or volume_z is None:
        return None
    if abs(price_z) < _PRICE_Z or volume_z < _VOLUME_Z:
        return None
    return {
        "key": key,
        "label": label,
        "type": typ,
        "price_z": round(price_z, 2),
        "volume_z": round(volume_z, 2),
        "change_pct": round(returns[-1] * 100, 2),
        "severity": _severity(price_z),
        "last": round(closes[-1], 4),
        "asof": asof,
    }


def _scan_sync() -> list[dict]:
    """Reyestri toplu çək (tək yf çağırışı) və hər aktivi yoxla."""
    syms = [s for _, _, s, _, _ in ASSETS]
    try:
        df = yf.download(
            " ".join(syms), period="6mo", interval="1d",
            auto_adjust=True, progress=False, threads=True,
        )
    except Exception:  # noqa: BLE001
        return []
    if df is None or df.empty:
        return []
    closes = df.get("Close")
    volumes = df.get("Volume")
    if closes is None:
        return []

    asof = str(closes.index[-1].date()) if len(closes.index) else ""
    out: list[dict] = []
    for key, label, sym, typ, _dec in ASSETS:
        try:
            c = closes[sym].dropna() if sym in closes else None
            if c is None or len(c) < 30:
                continue
            cl = [float(x) for x in c]
            vl: list[float] = []
            if volumes is not None and sym in volumes:
                v = volumes[sym].dropna()
                vl = [float(x) for x in v if x and float(x) > 0]
            res = _evaluate(key, label, typ, cl, vl, asof)
            if res:
                out.append(res)
        except (KeyError, IndexError, ValueError, TypeError):
            continue
    # Şiddətə görə sırala (ekstremal əvvəl), sonra |price_z|.
    rank = {"extreme": 0, "high": 1, "medium": 2}
    out.sort(key=lambda a: (rank[a["severity"]], -abs(a["price_z"])))
    return out


async def scan_all(force: bool = False) -> list[dict]:
    """Bütün reyestri yoxla (5 dəq keş). Anomaliyalar siyahısı."""
    now = time.time()
    if not force and _cache["data"] and now - _cache["ts"] < _TTL:
        return _cache["data"]
    data = await asyncio.to_thread(_scan_sync)
    if data or not _cache["data"]:
        _cache["ts"] = now
        _cache["data"] = data
    return _cache["data"]
