"""HS256 access token (mint + decode). Refresh token JWT DEYİL (bax auth_session).

Niyə HS256: bir imzalayan/bir yoxlayan (eyni proses) → açar-paylama problemi yoxdur,
EdDSA/RS256-nın həll etdiyi məsələ mövcud deyil. İki QƏTİ qayda decode-da:
- `algorithms=["HS256"]` — HEÇ VAXT başlıqdan (alg confusion + alg:none öldürülür).
- `claims["typ"] == "access"` — token-type confusion öldürülür.
Hər ikisi ayrıca regression testi alır (test_jwt).

Rotasiya: JWT_SECRET (imza+yoxlama) + JWT_SECRET_PREVIOUS (yalnız yoxlama). Sıfır-downtime
(refresh token-lər opaque DB sətirləridir → toxunulmur). Dev-də secret boşdursa
hardcoded dev açar + CRITICAL log (footgun: ENVIRONMENT=development ilə deploy = bypass).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

logger = logging.getLogger("nexusiq.jwt")

# Dev fallback — YALNIZ environment=development və secret boş olanda. Prod-da
# validate_runtime() boot-u dayandırır, ona görə bura prod-da çatılmır.
_DEV_FALLBACK_SECRET = "dev-insecure-nexusiq-jwt-key-CHANGE-ME-not-for-production"
_warned_dev = False


def _sign_secret() -> str:
    s = settings.jwt_secret
    if s:
        return s
    if settings.is_dev:
        global _warned_dev
        if not _warned_dev:
            logger.critical(
                "JWT_SECRET boşdur → DEV fallback açar işlədilir. PROD-da ASLA "
                "(ENVIRONMENT=development ilə deploy = repo-məlum açar = auth bypass)."
            )
            _warned_dev = True
        return _DEV_FALLBACK_SECRET
    raise RuntimeError("JWT_SECRET təyin olunmayıb (prod).")


def _verify_secrets() -> list[str]:
    secrets_list = [_sign_secret()]
    if settings.jwt_secret_previous:
        secrets_list.append(settings.jwt_secret_previous)
    return secrets_list


def mint_access(user_id: str, sid: str, tv: int) -> str:
    """access token. `tv` = user.sessions_valid_from epoch (logout-all yoxlaması üçün)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "sid": str(sid),
        "typ": "access",
        "tv": int(tv),
        "iat": now,
        "exp": now + timedelta(seconds=settings.access_ttl_seconds),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(payload, _sign_secret(), algorithm="HS256")


_REQUIRED = ["exp", "iat", "sub", "sid", "typ", "tv"]


def decode_access(token: str) -> dict:
    """access token-i doğrula. Uğursuzluqda PyJWT istisnası atır:
    - ExpiredSignatureError → çağırıcı `token_expired` (refresh yolu)
    - digər InvalidTokenError → `unauthenticated`
    """
    last_sig_err: jwt.InvalidTokenError | None = None
    for secret in _verify_secrets():
        try:
            claims = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],   # HEÇ VAXT başlıqdan — alg confusion / alg:none bağlı
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
                options={"require": _REQUIRED},
            )
        except jwt.ExpiredSignatureError:
            raise  # imza düzdür, sadəcə vaxtı bitib — previous secret sınamağa dəyməz
        except jwt.InvalidSignatureError as e:
            last_sig_err = e
            continue  # yanlış secret ola bilər → previous-u sına
        # digər InvalidTokenError (iss/aud/missing claim) → strukturca yararsız, dərhal at
        if claims.get("typ") != "access":
            raise jwt.InvalidTokenError("token type is not 'access'")
        return claims
    raise last_sig_err or jwt.InvalidTokenError("invalid token")
