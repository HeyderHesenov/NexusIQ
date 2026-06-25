"""İqtisadi təqvim — ForexFactory pulsuz həftəlik XML (faireconomy mirror).

Rəsmi API yoxdur; bu açıq XML lent pulsuzdur. Yüksək/orta təsirli hadisələr.
Nəticə 30 dəqiqə keşlənir.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import httpx

_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
_UA = {"User-Agent": "Mozilla/5.0 (NexusIQ)"}
_TTL = 1800.0
_cache: list | None = None
_cache_at = 0.0

_KEEP = {"High", "Medium"}


def _not_past(date_str: str) -> bool:
    """Hadisə bu gün və ya gələcəkdirsə True (gün granulyarlığı).

    XML tarix formatı `MM-DD-YYYY`. Parse alınmazsa təhlükəsiz tərəfdə saxla.
    """
    try:
        d = datetime.strptime(date_str, "%m-%d-%Y").date()
    except ValueError:
        return True
    return d >= datetime.now(timezone.utc).date()


def _parse(xml: str) -> list[dict]:
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
                "forecast": (ev.findtext("forecast") or "").strip(),
                "previous": (ev.findtext("previous") or "").strip(),
            }
        )
    return out[:40]


async def get_calendar() -> list[dict]:
    """Bu həftənin yüksək/orta təsirli hadisələri. Xəta → son keş / boş."""
    global _cache, _cache_at
    now = time.monotonic()
    if _cache is not None and now - _cache_at < _TTL:
        return _cache
    try:
        async with httpx.AsyncClient(headers=_UA, timeout=12.0) as client:
            r = await client.get(_URL)
            r.raise_for_status()
            events = _parse(r.text)
    except Exception:  # noqa: BLE001
        return _cache or []
    _cache, _cache_at = events, now
    return events
