"""Auth cookie set/clear/read — tək mənbə.

Ad `cookie_secure`-dan törəyir: secure→`__Host-` prefiks (host-only, Path=/, Domain yox),
əks halda çılpaq ad. Oxuyucu YALNIZ mühitə uyğun adı qəbul edir (dual-name = downgrade orakulu).
Access=Lax (inbound-link UX), Refresh=Strict (30-gün oğurluq dəyəri), CSRF=JS-oxunan.
"""
from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

_AT = "nexusiq_at"
_RT = "nexusiq_rt"
_CSRF = "nexusiq_csrf"
_GNONCE = "nexusiq_gnonce"


def _name(base: str) -> str:
    return f"{settings.cookie_prefix}{base}"


def access_name() -> str:
    return _name(_AT)


def refresh_name() -> str:
    return _name(_RT)


def csrf_name() -> str:
    return _name(_CSRF)


def gnonce_name() -> str:
    return _name(_GNONCE)


def set_access_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        access_name(), token,
        max_age=settings.access_ttl_seconds, path="/",
        secure=settings.cookie_secure, httponly=True, samesite="lax",
    )


def set_refresh_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        refresh_name(), token,
        max_age=settings.refresh_absolute_days * 86400, path="/",
        secure=settings.cookie_secure, httponly=True, samesite="strict",
    )


def set_csrf_cookie(resp: Response, value: str) -> None:
    # httponly=False — klient JS oxuyub X-CSRF-Token başlığında əks etdirir (double-submit).
    resp.set_cookie(
        csrf_name(), value,
        max_age=settings.refresh_absolute_days * 86400, path="/",
        secure=settings.cookie_secure, httponly=False, samesite="lax",
    )


def set_gnonce_cookie(resp: Response, value: str) -> None:
    resp.set_cookie(
        gnonce_name(), value,
        max_age=300, path="/",
        secure=settings.cookie_secure, httponly=True, samesite="lax",
    )


def clear_auth_cookies(resp: Response) -> None:
    for n in (access_name(), refresh_name(), csrf_name()):
        resp.delete_cookie(n, path="/", secure=settings.cookie_secure, samesite="lax")


def read_access(request: Request) -> str | None:
    return request.cookies.get(access_name())


def read_refresh(request: Request) -> str | None:
    return request.cookies.get(refresh_name())


def read_csrf(request: Request) -> str | None:
    return request.cookies.get(csrf_name())


def read_gnonce(request: Request) -> str | None:
    return request.cookies.get(gnonce_name())
