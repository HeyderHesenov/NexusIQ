"""Autentifikasiya dependency-ləri. Sərhəd BURADIR — AuthGate deyil.

`require_user` maşın-oxunan `code` qaytarır (lib/api.ts məhz `token_expired`-də refresh
edir; `unauthenticated`/`session_revoked`-da login ekranına gedir — yoxsa sonsuz refresh
döngüsü). logout-all: token-in `tv`-si (mint vaxtı sessions_valid_from epoxu) cari DB
dəyərindən kiçikdirsə rədd — 60s in-proses keş ilə (dəqiqədə bir indeksli oxu).
"""
from __future__ import annotations

import time
import uuid

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cookies, jwtsvc
from app.core.config import settings
from app.db.session import get_db
from app.models import User


class AuthError(HTTPException):
    """detail={'code': ...} — frontend koda görə davranır (retry vs login)."""

    def __init__(self, status_code: int, code: str) -> None:
        super().__init__(status_code=status_code, detail={"code": code})


# user_id → (sessions_valid_from datetime, monotonic expiry)
_valid_from_cache: dict[uuid.UUID, tuple[object, float]] = {}


async def _cached_valid_from(db: AsyncSession, user_id: uuid.UUID):
    now = time.monotonic()
    ent = _valid_from_cache.get(user_id)
    if ent and ent[1] > now:
        return ent[0]
    vf = await db.scalar(select(User.sessions_valid_from).where(User.id == user_id))
    if vf is not None:
        _valid_from_cache[user_id] = (vf, now + settings.sessions_valid_from_cache_ttl)
    return vf


def _clear_valid_from_cache(user_id: uuid.UUID | None = None) -> None:
    """Test / logout-all sonrası dərhal təsir üçün."""
    if user_id is None:
        _valid_from_cache.clear()
    else:
        _valid_from_cache.pop(user_id, None)


async def _authenticate(
    request: Request, db: AsyncSession, *, enforce_email_verification: bool
) -> User:
    token = cookies.read_access(request)
    if not token:
        raise AuthError(401, "unauthenticated")
    try:
        claims = jwtsvc.decode_access(token)
    except jwt.ExpiredSignatureError:
        raise AuthError(401, "token_expired")
    except jwt.InvalidTokenError:
        raise AuthError(401, "unauthenticated")

    try:
        uid = uuid.UUID(str(claims["sub"]))
    except (ValueError, KeyError):
        raise AuthError(401, "unauthenticated")

    user = await db.scalar(select(User).where(User.id == uid))
    if user is None:
        raise AuthError(401, "unauthenticated")
    if not user.is_active:
        raise AuthError(403, "account_disabled")

    vf = await _cached_valid_from(db, uid)
    if vf is not None and int(claims.get("tv", 0)) < int(vf.timestamp()):
        raise AuthError(401, "session_revoked")

    if (
        enforce_email_verification
        and settings.email_verification_required
        and user.email_verified_at is None
    ):
        raise AuthError(403, "email_not_verified")

    request.state.user_id = str(uid)
    return user


async def require_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    return await _authenticate(request, db, enforce_email_verification=True)


async def require_user_allow_unverified(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    """`/auth/me` üçün: təsdiqlənməmiş email-də belə istifadəçini qaytar (UI 'təsdiqlə'
    vəziyyəti render etsin). email_verification qapısı burada tətbiq OLUNMUR."""
    return await _authenticate(request, db, enforce_email_verification=False)


async def get_current_user_optional(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User | None:
    """Heç vaxt raise etmir — publik route-ları şəxsiləşdirmək üçün."""
    try:
        return await require_user(request, db)
    except HTTPException:
        return None


def owned(model, *, param: str = "id"):
    """Tək-sətir sahiblik dependency-si. 404 (403 DEYİL — 403 sətrin mövcudluğunu
    təsdiqləyən enumerasiya orakuludur)."""

    async def _dep(
        request: Request,
        user: User = Depends(require_user),
        db: AsyncSession = Depends(get_db),
    ):
        row_id = request.path_params.get(param)
        obj = await db.scalar(
            select(model).where(model.id == row_id, model.user_id == user.id)
        )
        if obj is None:
            raise HTTPException(status_code=404)
        return obj

    return _dep
