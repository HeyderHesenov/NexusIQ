"""Google ID-token yoxlaması (identity axını) + replay-qoruyan nonce.

Access token DEYİL, ID token: access token Google-a ünvanlanıb, bizə heç nə sübut
etmir; ID token bizim client_id-ə imzalanmış iddiadır (offline yoxlanır). `aud ==
GOOGLE_CLIENT_ID` bütün işi görən yoxlamadır. PyJWT[crypto] + PyJWKClient (google-auth
QƏSDƏN YOX — httpx-only bazaya requests gətirərdi). JWKS URL sabit → SSRF səthi yoxdur.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac

import jwt
from jwt import PyJWKClient

from app.core.config import settings

_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}

# Sync klient → to_thread. Cached JWKS + kid rotasiyası.
_jwk_client = PyJWKClient(_JWKS_URL, cache_keys=True, lifespan=21600, timeout=5)


class GoogleError(Exception):
    """ID-token yoxlaması uğursuz (imza/aud/iss/exp/nonce/email_verified)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class GoogleNotConfigured(Exception):
    """GOOGLE_CLIENT_ID təyin olunmayıb → 503 (heç vaxt uğur yolu)."""


def _get_signing_key(credential: str):
    # Test monkeypatch nöqtəsi.
    return _jwk_client.get_signing_key_from_jwt(credential)


async def verify_id_token(credential: str, *, nonce_expected: str | None) -> dict:
    if not settings.google_client_id:
        raise GoogleNotConfigured()

    try:
        signing_key = await asyncio.to_thread(_get_signing_key, credential)
    except Exception as exc:  # JWKS/kid problemləri
        raise GoogleError(f"jwks:{type(exc).__name__}") from exc

    try:
        claims = jwt.decode(
            credential,
            signing_key.key,
            algorithms=["RS256"],           # pinlənib — başlıqdan alg YOX
            audience=settings.google_client_id,  # aud == bizim client_id
            options={"require": ["exp", "iat", "aud", "iss", "sub"]},
            leeway=60,                       # ≤60s exp/iat skew
        )
    except jwt.InvalidTokenError as exc:
        raise GoogleError(f"jwt:{type(exc).__name__}") from exc

    if claims.get("iss") not in _ISSUERS:
        raise GoogleError("iss")
    if not claims.get("sub"):
        raise GoogleError("sub")
    if not claims.get("email"):
        raise GoogleError("email")
    if claims.get("email_verified") is not True:
        raise GoogleError("email_verified")
    if nonce_expected is None or claims.get("nonce") != nonce_expected:
        raise GoogleError("nonce")

    return claims


# ---- Nonce (stateless, HMAC-imzalı, tək-istifadə cookie) ----

def _nonce_key() -> bytes:
    key = settings.csrf_secret or ("dev-nonce-fallback-not-for-prod" if settings.is_dev else "")
    return key.encode("utf-8")


def _nonce_mac(raw: str) -> str:
    return hmac.new(_nonce_key(), raw.encode("utf-8"), hashlib.sha256).hexdigest()


def sign_nonce(raw: str) -> str:
    return f"{raw}.{_nonce_mac(raw)}"


def extract_nonce(signed: str | None) -> str | None:
    """Cookie dəyərindən xam nonce-i çıxar (HMAC doğru olsa). Yoxsa None."""
    if not signed:
        return None
    try:
        raw, mac = signed.split(".", 1)
    except ValueError:
        return None
    if hmac.compare_digest(mac, _nonce_mac(raw)):
        return raw
    return None


def safe_avatar(picture: str | None) -> str | None:
    """<img src> olacaq → https + googleusercontent.com host, əks halda at."""
    if not picture or not picture.startswith("https://"):
        return None
    from urllib.parse import urlsplit

    host = urlsplit(picture).hostname or ""
    return picture if host.endswith("googleusercontent.com") else None
