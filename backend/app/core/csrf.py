"""CSRF müdafiəsi — iki müstəqil qat, TƏK ASGI middleware (bütün route-lara).

`Content-Type: application/json` TƏK BAŞINA kifayət deyil: boş `type`-lı Blob heç bir
CT başlığı göndərmir → preflight yoxdur → cookie qoşulur → FastAPI JSON yolunu tutur.
Ona görə:
- Qat 1 (əsas): Origin/Referer allowlist. Absent/uyğunsuz → 403. Faktiki təhlükəni
  (cross-origin sorğu) birbaşa hədəfləyir, stateless və pulsuz.
- Qat 2 (ikincili): HMAC-imzalı double-submit, `sid`-ə bağlı. YALNIZ access cookie
  olanda işə düşür (sessiya yoxdursa qorunacaq bir şey yoxdur → BUGÜN no-op). HMAC-sid
  bağlaması plain double-submit-in sibling-subdomain bypass-ını öldürür.

Middleware sırası (main.py): CORS → CSRF → BodyLimit → app. Heç bir route iştirak etmir
→ heç biri CSRF-i unuda bilməz.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from urllib.parse import urlsplit

from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core import cookies
from app.core.config import settings
from app.core.jwtsvc import peek_sid

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
_EXEMPT_PATHS: frozenset[str] = frozenset()  # genişlənə bilər (məs. webhook)


def _csrf_key() -> bytes:
    key = settings.csrf_secret or ("dev-csrf-fallback-not-for-prod" if settings.is_dev else "")
    return key.encode("utf-8")


def _mac(sid: str, nonce: str) -> str:
    return hmac.new(_csrf_key(), f"{sid}|{nonce}".encode("utf-8"), hashlib.sha256).hexdigest()


def make_csrf_token(sid: str) -> str:
    """`<nonce>.<hmac(csrf_secret, sid|nonce)>`. Pre-auth üçün sid=''."""
    nonce = secrets.token_urlsafe(16)
    return f"{nonce}.{_mac(sid, nonce)}"


def verify_csrf_token(token: str, sid: str) -> bool:
    try:
        nonce, mac = token.split(".", 1)
    except ValueError:
        return False
    return hmac.compare_digest(mac, _mac(sid, nonce))


def _request_origin(req: Request) -> str | None:
    origin = req.headers.get("origin")
    if origin:
        return origin
    ref = req.headers.get("referer")
    if ref:
        parts = urlsplit(ref)
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"
    return None


class CsrfMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        req = Request(scope)
        if req.method in _SAFE_METHODS or req.url.path in _EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        # ---- Qat 1: Origin/Referer ----
        origin = _request_origin(req)
        if origin is None or origin not in settings.cors_origins_list:
            await self._deny(scope, receive, send, "csrf_origin_mismatch")
            return

        # ---- Qat 2: yalnız access cookie varsa (sessiya) ----
        at = req.cookies.get(cookies.access_name())
        if at:
            csrf_cookie = req.cookies.get(cookies.csrf_name())
            csrf_header = req.headers.get("x-csrf-token")
            if (
                not csrf_cookie
                or not csrf_header
                or not hmac.compare_digest(csrf_cookie, csrf_header)
            ):
                await self._deny(scope, receive, send, "csrf_token_missing")
                return
            sid = peek_sid(at)
            if not sid or not verify_csrf_token(csrf_cookie, sid):
                await self._deny(scope, receive, send, "csrf_token_invalid")
                return

        await self.app(scope, receive, send)

    async def _deny(self, scope, receive, send, code: str) -> None:
        resp = JSONResponse(
            {"detail": "CSRF yoxlaması uğursuz", "code": code}, status_code=403
        )
        await resp(scope, receive, send)
