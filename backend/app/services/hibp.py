"""HIBP breach yoxlaması — k-anonimlik, env-qapılı, fail-OPEN.

Yalnız register/change-də (login-də YOX). Parolun ilk 5 SHA-1 hex simvolu göndərilir,
~800 suffiks qayıdır, lokal uyğunlaşdırma → parol prosesi tərk etmir. Fail-OPEN, çünki
KEYFİYYƏT nəzarətidir, sərhəd deyil — HIBP kəsintisi qeydiyyatı dayandırmamalıdır.
Sabit host → SSRF səthi yoxdur (netguard lazım deyil). 1 saat neqativ keş.
"""
from __future__ import annotations

import hashlib
import logging
import time

import httpx

from app.core.config import settings

logger = logging.getLogger("nexusiq.hibp")

_API = "https://api.pwnedpasswords.com/range/"
_TIMEOUT = 2.0
_NEG_TTL = 3600.0
# prefix → (pwned?, expiry) — yalnız NEQATİV (pwned=False) keşlənir.
_neg_cache: dict[str, float] = {}


async def is_pwned(password: str) -> bool:
    """Parol məlum breach-də görünübmü. Söndürülübsə və ya xəta olsa False (fail-open)."""
    if not settings.hibp_enabled:
        return False

    sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha1[:5], sha1[5:]

    exp = _neg_cache.get(prefix)
    if exp and exp > time.monotonic():
        return False  # bu prefiks yaxında "təmiz" idi (neqativ keş)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(f"{_API}{prefix}", headers={"Add-Padding": "true"})
            r.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — fail-open, hər cür xəta udulur
        logger.warning("HIBP əlçatmaz (fail-open): %s", type(exc).__name__)
        return False

    for line in r.text.splitlines():
        hashsuf, _, count = line.partition(":")
        if hashsuf.strip().upper() == suffix and count.strip() not in ("", "0"):
            return True

    _neg_cache[prefix] = time.monotonic() + _NEG_TTL
    return False
