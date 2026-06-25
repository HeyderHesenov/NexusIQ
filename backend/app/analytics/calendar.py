"""İqtisadi təqvim — gələcək ~3 həftəlik yüksək/orta təsirli hadisələr.

Primary mənbə: TradingView-in açıq economic-calendar endpoint-i (key-siz,
`from`/`to` pəncərəsi → çoxhəftəlik əhatə). Endpoint düşərsə ForexFactory-nin
pulsuz həftəlik XML lentinə (faireconomy mirror) fallback edilir. İkisi də
rəsmi olmayan açıq lentlərdir. Nəticə 30 dəqiqə keşlənir.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import httpx

# Primary — TradingView (çoxhəftəlik, importance + forecast/previous)
_TV_URL = "https://economic-calendar.tradingview.com/events"
_TV_HEADERS = {
    "User-Agent": "Mozilla/5.0 (NexusIQ)",
    "Origin": "https://www.tradingview.com",
    "Referer": "https://www.tradingview.com/",
}
_COUNTRIES = "US,EU,GB,JP,CA,AU,CN,CH,NZ"
_WINDOW_DAYS = 31  # bugündən ~1 ay irəli
_IMPACT = {1: "High", 0: "Medium"}  # -1 (Low) atılır

# Fallback — ForexFactory (yalnız bu həftə)
_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
_UA = {"User-Agent": "Mozilla/5.0 (NexusIQ)"}

_TTL = 1800.0
_cache: list | None = None
_cache_at = 0.0
_CAP = 300

_KEEP = {"High", "Medium"}


def _not_past(date_str: str) -> bool:
    """Hadisə bu gün və ya gələcəkdirsə True (gün granulyarlığı).

    Tarix formatı `MM-DD-YYYY`. Parse alınmazsa təhlükəsiz tərəfdə saxla.
    """
    try:
        d = datetime.strptime(date_str, "%m-%d-%Y").date()
    except ValueError:
        return True
    return d >= datetime.now(timezone.utc).date()


def _fmt(value, unit, scale) -> str:
    """TradingView rəqəmini ForexFactory-bənzər string-ə çevir: 4.4+%→"4.4%", 225+K→"225K"."""
    if value is None:
        return ""
    num = f"{value:g}" if isinstance(value, (int, float)) else str(value).strip()
    return f"{num}{(scale or '').strip()}{(unit or '').strip()}"


def _parse_tv(payload: dict) -> list[dict]:
    """TradingView cavabını `CalEvent` formasına map et."""
    out: list[dict] = []
    for ev in payload.get("result") or []:
        impact = _IMPACT.get(ev.get("importance"))
        if impact is None:  # Low (-1) və ya naməlum → at
            continue
        try:
            dt = datetime.fromisoformat(
                (ev.get("date") or "").replace("Z", "+00:00")
            ).astimezone(timezone.utc)
        except ValueError:
            continue
        date = dt.strftime("%m-%d-%Y")
        if not _not_past(date):
            continue
        out.append(
            {
                "title": (ev.get("title") or "").strip(),
                "country": (ev.get("currency") or ev.get("country") or "").strip(),
                "date": date,
                "time": dt.strftime("%I:%M%p").lstrip("0").lower(),
                "impact": impact,
                "actual": _fmt(ev.get("actual"), ev.get("unit"), ev.get("scale")),
                "forecast": _fmt(ev.get("forecast"), ev.get("unit"), ev.get("scale")),
                "previous": _fmt(ev.get("previous"), ev.get("unit"), ev.get("scale")),
                "_ts": dt.timestamp(),
            }
        )
    out.sort(key=lambda e: e["_ts"])
    for e in out:
        del e["_ts"]
    return out[:_CAP]


def _parse(xml: str) -> list[dict]:
    """ForexFactory XML fallback → `CalEvent`."""
    root = ET.fromstring(xml)
    out: list[dict] = []
    for ev in root.findall("event"):
        impact = (ev.findtext("impact") or "").strip()
        if impact not in _KEEP:
            continue
        date = (ev.findtext("date") or "").strip()
        if not _not_past(date):  # keçmiş günləri at — öndə bugün+gələcək qalsın
            continue
        out.append(
            {
                "title": (ev.findtext("title") or "").strip(),
                "country": (ev.findtext("country") or "").strip(),
                "date": date,
                "time": (ev.findtext("time") or "").strip(),
                "impact": impact,
                "actual": "",
                "forecast": (ev.findtext("forecast") or "").strip(),
                "previous": (ev.findtext("previous") or "").strip(),
            }
        )
    return out[:_CAP]


async def _fetch() -> list[dict]:
    """Primary TradingView; xəta olarsa ForexFactory fallback."""
    now = datetime.now(timezone.utc)
    params = {
        "from": now.strftime("%Y-%m-%dT00:00:00.000Z"),
        "to": (now + timedelta(days=_WINDOW_DAYS)).strftime("%Y-%m-%dT00:00:00.000Z"),
        "countries": _COUNTRIES,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.get(_TV_URL, params=params, headers=_TV_HEADERS)
            r.raise_for_status()
            events = _parse_tv(r.json())
            if events:
                return events
        except Exception:  # noqa: BLE001 — fallback-a düş
            pass
        r = await client.get(_URL, headers=_UA)
        r.raise_for_status()
        return _parse(r.text)


async def get_calendar() -> list[dict]:
    """Gələcək ~3 həftənin yüksək/orta təsirli hadisələri. Xəta → son keş / boş."""
    global _cache, _cache_at
    now = time.monotonic()
    if _cache is not None and now - _cache_at < _TTL:
        return _cache
    try:
        events = await _fetch()
    except Exception:  # noqa: BLE001
        return _cache or []
    _cache, _cache_at = events, now
    return events
