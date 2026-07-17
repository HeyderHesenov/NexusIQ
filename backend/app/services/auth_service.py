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
from app.models import AuthSession, PasswordResetToken, User


class InvalidRefresh(Exception):
    """Uyğun/etibarlı sessiya yoxdur → 401, login yenidən."""


class ReuseDetected(Exception):
    """Oğurlanmış/təkrar-istifadə token → bütün sessiyalar ləğv edildi → 401."""


class LoginFailed(Exception):
    """Yanlış parol VƏ ya naməlum email → eyni generik 401 (enumerasiya yox)."""


class AccountLocked(Exception):
    """Hesab müvəqqəti kilidli → 429 + Retry-After (mövcudluq sızır — qəbul edilib)."""

    def __init__(self, retry_after: int) -> None:
        super().__init__("account locked")
        self.retry_after = retry_after


def normalize_email(email: str) -> str:
    """Yalnız lowercase — gmail nöqtə/+tag aliasing ETMƏ (merge bug-ları)."""
    return email.strip().lower()


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


async def revoke_by_refresh_token(session: AsyncSession, raw_token: str) -> None:
    """logout: refresh token-in aid olduğu sessiyanı ləğv et (idempotent)."""
    h = security.hash_token(raw_token)
    await session.execute(
        update(AuthSession)
        .where(
            or_(
                AuthSession.refresh_token_hash == h,
                AuthSession.previous_token_hash == h,
            ),
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=func.now(), revoked_reason="logout")
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


# ==================== İstifadəçi + login ====================

_LOCK_THRESHOLD = 5


def _lock_seconds(count: int) -> int:
    """5-ci uğursuzluqdan eksponensial backoff, maks 15 dəq. Daimi kilid YOX
    (o, hesab-DoS primitividir)."""
    return min(2 ** (count - 4), 900)


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    return await session.scalar(
        select(User).where(User.email == normalize_email(email))
    )


async def create_user(
    session: AsyncSession,
    email: str,
    *,
    password_hash: str | None,
    display_name: str | None = None,
    email_verified: bool = False,
    avatar_url: str | None = None,
) -> User:
    user = User(
        email=normalize_email(email),
        password_hash=password_hash,
        display_name=display_name,
        avatar_url=avatar_url,
    )
    if email_verified:
        user.email_verified_at = _now()
    session.add(user)
    await session.flush()
    return user


async def _register_failure(session: AsyncSession, user: User) -> None:
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= _LOCK_THRESHOLD:
        user.locked_until = _now() + timedelta(seconds=_lock_seconds(user.failed_login_count))
    await session.commit()  # sayğac PERSIST olmalı (route 401/429 qaytaracaq)


async def authenticate(session: AsyncSession, email: str, password: str) -> User:
    """Uğurda User; yoxsa LoginFailed / AccountLocked.

    QAYDA: kilid yoxlaması Argon2-dən ƏVVƏL (yoxsa login uzaqdan yaddaş tükəndirmə).
    """
    user = await get_user_by_email(session, email)
    now = _now()

    if user is not None and user.locked_until is not None and user.locked_until > now:
        raise AccountLocked(int((user.locked_until - now).total_seconds()) + 1)

    # Naməlum email VƏ ya Google-only (parolsuz) → dummy verify (timing) + generik fail.
    # Short-circuit ETMƏ ki, "bu hesabın parolu yoxdur" sızmasın.
    if user is None or user.password_hash is None:
        security.verify_password(security.DUMMY_HASH, password)
        if user is not None:
            await _register_failure(session, user)
        raise LoginFailed()

    if security.verify_password(user.password_hash, password):
        user.failed_login_count = 0
        user.locked_until = None
        user.last_login_at = now
        if security.needs_rehash(user.password_hash):
            user.password_hash = security.hash_password(password)
        return user

    await _register_failure(session, user)
    raise LoginFailed()


# ==================== Parol dəyiş / reset ====================

async def change_password(
    session: AsyncSession, user: User, new_password: str, *, current_sid
) -> None:
    """Parolu dəyiş: cari `sid` XARİC bütün sessiyaları ləğv et (dəyişəni ATMA);
    sessions_valid_from-u BUMP ETMƏ (yoxsa parolu dəyişən özü çıxarılar)."""
    user.password_hash = security.hash_password(new_password)
    await revoke_all_sessions(session, user.id, "password_change", exclude_sid=current_sid)


async def create_reset_token(
    session: AsyncSession, user: User, *, ip: str | None = None
) -> str:
    """Əvvəlki istifadə olunmamış tokenləri ləğv et, yeni 30-dəq token yarat (xam qaytar)."""
    await session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=func.now())
    )
    raw = security.generate_token()
    tok = PasswordResetToken(
        user_id=user.id,
        token_hash=security.hash_token(raw),
        expires_at=_now() + timedelta(minutes=30),
        requested_ip=ip,
    )
    session.add(tok)
    await session.flush()
    return raw


async def consume_reset_token(session: AsyncSession, raw: str) -> User | None:
    """Tək-istifadəlik: token etibarlıdırsa istifadəçini qaytar + used işarələ."""
    h = security.hash_token(raw)
    now = _now()
    tok = await session.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == h)
        .with_for_update()
    )
    if tok is None or tok.used_at is not None or tok.expires_at <= now:
        return None
    tok.used_at = now
    return await session.scalar(select(User).where(User.id == tok.user_id))


async def apply_password_reset(
    session: AsyncSession, user: User, new_password: str
) -> None:
    """Reset: yeni hash + BÜTÜN sessiyaları ləğv + sessions_valid_from bump (access-lər də ölsün).
    Auto-login YOX (link brauzer tarixçəsində qalır)."""
    user.password_hash = security.hash_password(new_password)
    await revoke_all_sessions(session, user.id, "reset")
    await bump_sessions_valid_from(session, user.id)
