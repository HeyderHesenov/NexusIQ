"""Sessiya yaratma + refresh rotasiyası + reuse detection (§2.4).

Bütün rotasiya bir tranzaksiyada, sessiya sətrində `.with_for_update()` ilə (TOCTOU
bağlı). Grace window (10s) iki-tab benign race-i həqiqi oğurluqdan ayırır — bu,
rotasiyanın prod-da geri qaytarılmasının ƏN çox rast gəlinən səbəbidir.

Refresh token opaque (256-bit CSPRNG); DB-də yalnız SHA-256 hash saxlanır.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import settings
from app.models import AuthSession, User


class InvalidRefresh(Exception):
    """Uyğun/etibarlı sessiya yoxdur → 401, login yenidən."""


class ReuseDetected(Exception):
    """Oğurlanmış/təkrar-istifadə token → bütün sessiyalar ləğv edildi → 401."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_session(
    session: AsyncSession,
    user: User,
    *,
    user_agent: str | None = None,
    ip: str | None = None,
) -> tuple[str, AuthSession]:
    """Yeni sessiya + xam refresh token qaytarır (yalnız burada görünür)."""
    raw = security.generate_token()
    now = _now()
    sess = AuthSession(
        user_id=user.id,
        refresh_token_hash=security.hash_token(raw),
        issued_at=now,
        expires_at=now + timedelta(days=settings.refresh_absolute_days),
        last_used_at=now,
        user_agent=(user_agent or None) and user_agent[:200],
        ip=ip,
    )
    session.add(sess)
    await session.flush()  # sess.id (JWT sid) doldurulsun
    return raw, sess


async def revoke_session(
    session: AsyncSession, sid, reason: str
) -> None:
    await session.execute(
        update(AuthSession)
        .where(AuthSession.id == sid, AuthSession.revoked_at.is_(None))
        .values(revoked_at=func.now(), revoked_reason=reason)
    )


async def revoke_all_sessions(
    session: AsyncSession, user_id, reason: str, *, exclude_sid=None
) -> None:
    stmt = update(AuthSession).where(
        AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)
    )
    if exclude_sid is not None:
        stmt = stmt.where(AuthSession.id != exclude_sid)
    await session.execute(stmt.values(revoked_at=func.now(), revoked_reason=reason))


async def bump_sessions_valid_from(session: AsyncSession, user_id) -> None:
    """logout-all / reset: bu vaxtdan əvvəlki access token-lər də rədd olunsun."""
    await session.execute(
        update(User).where(User.id == user_id).values(sessions_valid_from=func.now())
    )


async def rotate_refresh(
    session: AsyncSession,
    raw_token: str,
    *,
    user_agent: str | None = None,
    ip: str | None = None,
) -> tuple[str | None, AuthSession]:
    """§2.4 rotasiya + reuse detection. Bir tranzaksiya, FOR UPDATE.

    Qaytarır:
      (new_raw, sess)  → rotasiya oldu: yeni refresh cookie qoy.
      (None, sess)     → benign grace race: yeni access ver, refresh cookie DƏYİŞMƏ.
    Atır:
      InvalidRefresh   → uyğun/etibarlı sessiya yoxdur (401).
      ReuseDetected    → bütün sessiyalar ləğv olundu (commit olunur) (401).
    """
    h = security.hash_token(raw_token)
    now = _now()

    sess = await session.scalar(
        select(AuthSession)
        .where(
            or_(
                AuthSession.refresh_token_hash == h,
                AuthSession.previous_token_hash == h,
            )
        )
        .with_for_update()
    )
    if sess is None:
        # Heç bir dəyişiklik — bilinməyən token.
        raise InvalidRefresh("no matching session")

    # Ləğv olunmuş sessiyanın token-i təkrar istifadə → oğurluq siqnalı.
    if sess.revoked_at is not None:
        await revoke_all_sessions(session, sess.user_id, "reuse")
        await session.commit()  # ləğv PERSIST olmalıdır (route 401 qaytaracaq)
        raise ReuseDetected("reuse of a revoked session")

    # Vaxt bitib → sadəcə etibarsız (login yenidən).
    if sess.expires_at <= now:
        raise InvalidRefresh("absolute expiry")
    if (now - sess.last_used_at) > timedelta(days=settings.refresh_idle_days):
        raise InvalidRefresh("idle expiry")

    matched_previous = sess.previous_token_hash == h
    if matched_previous:
        within_grace = (
            sess.rotated_at is not None
            and (now - sess.rotated_at)
            <= timedelta(seconds=settings.rotation_grace_seconds)
        )
        if within_grace:
            # Benign race (iki tab): rotasiya ETMƏ, alarm ETMƏ. Access cari sessiyaya qarşı.
            sess.last_used_at = now
            return None, sess
        # Grace-dən kənar previous → oğurlanmış token.
        await revoke_all_sessions(session, sess.user_id, "reuse")
        await session.commit()
        raise ReuseDetected("previous token reused outside grace")

    # matched current → rotasiya et.
    new_raw = security.generate_token()
    sess.previous_token_hash = sess.refresh_token_hash
    sess.refresh_token_hash = security.hash_token(new_raw)
    sess.rotated_at = now
    sess.last_used_at = now
    if user_agent:
        sess.user_agent = user_agent[:200]
    if ip:
        sess.ip = ip
    return new_raw, sess
