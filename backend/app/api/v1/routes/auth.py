"""Auth route-ları: register / login / refresh / logout / logout-all / me / password / reset.

Enumerasiya: register + reset ADDITIV byte-identik cavab (202 {"ok":true}) + 250ms floor —
mövcudluq YALNIZ login-də sızır (kilid 429), o da qəsdən qəbul edilib. Login kilidi
Argon2-dən ƏVVƏL yoxlanır (yaddaş tükəndirmə qorusu).
"""
from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import cookies, csrf, jwtsvc
from app.core.auth import require_user, require_user_allow_unverified
from app.core.clientip import client_ip
from app.core.config import settings
from app.core.ratelimit import rate_limit
from app.core.security import PasswordPolicyError, validate_password
from app.db.session import get_db
from app.models import User
from app.schemas.auth import (
    LoginIn,
    OkOut,
    PasswordChangeIn,
    RegisterIn,
    ResetConfirmIn,
    ResetRequestIn,
    UserOut,
)
from app.services import auth_service, hibp
from app.services.email import get_email_sender

router = APIRouter()

_FLOOR = 0.25  # enumerasiya-safe zaman döşəməsi (register/reset)

# Rate limitlər (per-IP). Refresh per-user olmalı idi, amma user rotasiyadan sonra
# bilinir → per-IP təhlükəsizlik limiti kifayətdir.
_register_h = rate_limit("auth_register_h", settings.register_per_hour_ip, 3600)
_register_d = rate_limit("auth_register_d", settings.register_per_day_ip, 86400)
_login_m = rate_limit("auth_login_m", 10, 60)
_login_h = rate_limit("auth_login_h", 100, 3600)
_refresh_l = rate_limit("auth_refresh", 120, 3600)
_reset_l = rate_limit("auth_reset", 3, 3600)


def _err(status: int, code: str, headers: dict | None = None) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code}, headers=headers)


async def _floor_since(start: float) -> None:
    elapsed = time.monotonic() - start
    if elapsed < _FLOOR:
        await asyncio.sleep(_FLOOR - elapsed)


def _issue_cookies(resp, user: User, sess, *, raw_refresh: str | None) -> None:
    tv = int(user.sessions_valid_from.timestamp())
    cookies.set_access_cookie(resp, jwtsvc.mint_access(str(user.id), str(sess.id), tv))
    if raw_refresh is not None:  # benign refresh-də None → refresh cookie DƏYİŞMƏ
        cookies.set_refresh_cookie(resp, raw_refresh)
    cookies.set_csrf_cookie(resp, csrf.make_csrf_token(str(sess.id)))


def _user_response(user: User, sess, *, raw_refresh: str | None, status: int = 200) -> JSONResponse:
    resp = JSONResponse(UserOut.of(user).model_dump(by_alias=True), status_code=status)
    _issue_cookies(resp, user, sess, raw_refresh=raw_refresh)
    return resp


# ==================== register ====================

@router.post("/register")
async def register(
    payload: RegisterIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rh=Depends(_register_h),
    _rd=Depends(_register_d),
) -> JSONResponse:
    start = time.monotonic()
    # Parol yoxlaması existence-dən ƏVVƏL — heç bir mövcudluq sızmır.
    try:
        validate_password(payload.password)
    except PasswordPolicyError as e:
        raise _err(422, e.code)
    if await hibp.is_pwned(payload.password):
        raise _err(422, "password_breached")

    from app.core.security import hash_password

    existing = await auth_service.get_user_by_email(db, payload.email)
    if existing is None:
        await auth_service.create_user(
            db,
            payload.email,
            password_hash=hash_password(payload.password),
            display_name=payload.display_name,
        )
        await db.commit()
    else:
        # Mövcud email → sahibinə xəbər ver (console/SMTP). Cavab eynidir.
        await get_email_sender().send(
            existing.email,
            "NexusIQ — qeydiyyat cəhdi",
            "Kimsə bu email ilə qeydiyyatdan keçməyə çalışdı. Əgər bu sən deyilsənsə, "
            "nəzərə alma.",
        )

    await _floor_since(start)
    return JSONResponse(OkOut().model_dump(by_alias=True), status_code=202)


# ==================== login ====================

@router.post("/login")
async def login(
    payload: LoginIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _lm=Depends(_login_m),
    _lh=Depends(_login_h),
) -> JSONResponse:
    try:
        user = await auth_service.authenticate(db, payload.email, payload.password)
    except auth_service.AccountLocked as e:
        raise _err(429, "too_many_attempts", headers={"Retry-After": str(e.retry_after)})
    except auth_service.LoginFailed:
        raise _err(401, "invalid_credentials")

    raw_refresh, sess = await auth_service.create_session(
        db, user,
        user_agent=request.headers.get("user-agent"),
        ip=client_ip(request),
    )
    await db.commit()
    return _user_response(user, sess, raw_refresh=raw_refresh)


# ==================== refresh ====================

@router.post("/refresh")
async def refresh(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rl=Depends(_refresh_l),
) -> JSONResponse:
    raw = cookies.read_refresh(request)
    if not raw:
        resp = JSONResponse({"detail": {"code": "unauthenticated"}}, status_code=401)
        cookies.clear_auth_cookies(resp)
        return resp
    try:
        new_raw, sess = await auth_service.rotate_refresh(
            db, raw,
            user_agent=request.headers.get("user-agent"),
            ip=client_ip(request),
        )
    except auth_service.ReuseDetected:
        resp = JSONResponse({"detail": {"code": "session_revoked"}}, status_code=401)
        cookies.clear_auth_cookies(resp)
        return resp
    except auth_service.InvalidRefresh:
        resp = JSONResponse({"detail": {"code": "unauthenticated"}}, status_code=401)
        cookies.clear_auth_cookies(resp)
        return resp

    user = await db.scalar(select(User).where(User.id == sess.user_id))
    await db.commit()
    return _user_response(user, sess, raw_refresh=new_raw)


# ==================== logout / logout-all ====================

@router.post("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)) -> JSONResponse:
    raw = cookies.read_refresh(request)
    if raw:
        await auth_service.revoke_by_refresh_token(db, raw)
        await db.commit()
    resp = JSONResponse(OkOut().model_dump(by_alias=True))
    cookies.clear_auth_cookies(resp)
    return resp


@router.post("/logout-all")
async def logout_all(
    request: Request,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await auth_service.revoke_all_sessions(db, user.id, "logout_all")
    await auth_service.bump_sessions_valid_from(db, user.id)
    await db.commit()
    from app.core.auth import _clear_valid_from_cache

    _clear_valid_from_cache(user.id)
    resp = JSONResponse(OkOut().model_dump(by_alias=True))
    cookies.clear_auth_cookies(resp)
    return resp


# ==================== me ====================

@router.get("/me")
async def me(user: User = Depends(require_user_allow_unverified)) -> dict:
    return UserOut.of(user).model_dump(by_alias=True)


# ==================== password change ====================

@router.post("/password")
async def change_password(
    payload: PasswordChangeIn,
    request: Request,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not user.password_hash or not _verify(user.password_hash, payload.current_password):
        raise _err(401, "invalid_credentials")
    try:
        validate_password(payload.new_password)
    except PasswordPolicyError as e:
        raise _err(422, e.code)
    if await hibp.is_pwned(payload.new_password):
        raise _err(422, "password_breached")

    current_sid = getattr(request.state, "sid", None)
    await auth_service.change_password(db, user, payload.new_password, current_sid=current_sid)
    await db.commit()
    return OkOut().model_dump(by_alias=True)


def _verify(stored_hash: str, pw: str) -> bool:
    from app.core.security import verify_password

    return verify_password(stored_hash, pw)


# ==================== password reset ====================

@router.post("/password-reset/request")
async def reset_request(
    payload: ResetRequestIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _rl=Depends(_reset_l),
) -> JSONResponse:
    start = time.monotonic()
    user = await auth_service.get_user_by_email(db, payload.email)
    if user is not None:
        raw = await auth_service.create_reset_token(db, user, ip=client_ip(request))
        await db.commit()
        link = f"/reset?token={raw}"
        body = f"Parolu sıfırlamaq üçün: {link}\n30 dəqiqə etibarlıdır."
        if settings.auth_dev_expose_tokens and settings.is_dev:
            body += f"\n[DEV] token={raw}"
        await get_email_sender().send(user.email, "NexusIQ — parol sıfırlama", body)
    await _floor_since(start)
    return JSONResponse(OkOut().model_dump(by_alias=True), status_code=202)


@router.post("/password-reset/confirm")
async def reset_confirm(
    payload: ResetConfirmIn, db: AsyncSession = Depends(get_db)
) -> dict:
    try:
        validate_password(payload.password)
    except PasswordPolicyError as e:
        raise _err(422, e.code)
    if await hibp.is_pwned(payload.password):
        raise _err(422, "password_breached")

    user = await auth_service.consume_reset_token(db, payload.token)
    if user is None:
        raise _err(400, "invalid_token")
    await auth_service.apply_password_reset(db, user, payload.password)
    await db.commit()
    from app.core.auth import _clear_valid_from_cache

    _clear_valid_from_cache(user.id)
    return OkOut().model_dump(by_alias=True)  # auto-login YOX
