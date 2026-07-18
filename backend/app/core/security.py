"""Parol hash-ı (Argon2id) + token generasiya/hash + parol siyasəti.

Kritik qaydalar:
- `argon2-cffi` BİRBAŞA — `passlib` DEYİL (3.13-də silinən `crypt`-ə uzanır).
- Argon2id `t=3, m=64MiB, p=4` (RFC 9106 ikinci profil). 2 GiB profili DEYİL —
  memory-hard hash DoS gücləndiricisidir. Per-IP limit + locked_until yoxlaması
  Argon2-dən ƏVVƏL işləməlidir (yoxsa login uzaqdan yaddaş tükəndirmə primitividir).
- Refresh/reset/verify token-ləri SHA-256 (Argon2 YOX): 256-bit CSPRNG çıxışında
  brute-force ediləcək insan sirri yoxdur; Argon2 hər refresh-ə ~50ms əlavə edərdi.
- Tam PHC string saxlanır → Argon2 parametrləri hash ilə səyahət edir → parametrləri
  qaldırmaq konfiq dəyişikliyidir (migrasiya yox); köhnə hash-lar login-də rehash olunur.
"""
from __future__ import annotations

import hashlib
import secrets
import unicodedata

from argon2 import PasswordHasher
from argon2 import exceptions as argon2_exc

from app.core.config import settings


class PasswordPolicyError(ValueError):
    """Parol siyasəti pozuntusu — `code` i18n açarına xəritələnir (route qatı)."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _hasher() -> PasswordHasher:
    # Hər çağırışda cari settings-dən qurulur → testlər parametrləri aşağı sala bilir.
    # PasswordHasher yüngüldür (yalnız parametr saxlayır).
    return PasswordHasher(
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_kib,
        parallelism=settings.argon2_parallelism,
        hash_len=32,
        salt_len=16,
    )


def normalize_password(pw: str) -> str:
    """NFKC — eyni parolun fərqli Unicode təmsilləri eyni hash-a düşsün."""
    return unicodedata.normalize("NFKC", pw)


def validate_password(pw: str) -> None:
    """Siyasət yoxlaması (register/change). Pozularsa PasswordPolicyError qaldırır.

    Min 12 (2026 konsensusu), maks 128 (limitsiz giriş = CPU-yanma). Yalnız-boşluq rədd.
    """
    norm = normalize_password(pw)
    if len(norm) < settings.password_min_length:
        raise PasswordPolicyError("password_too_short")
    if len(norm) > settings.password_max_length:
        raise PasswordPolicyError("password_too_long")
    if not norm.strip():
        raise PasswordPolicyError("password_invalid")


def hash_password(pw: str) -> str:
    """Argon2id PHC string qaytarır (NFKC normalizasiya edilmiş parol üçün)."""
    return _hasher().hash(normalize_password(pw))


def verify_password(stored_hash: str, pw: str) -> bool:
    """Sabit-vaxtlı yoxlama. Uyğunsuz/pozuq hash → False (istisna atmır)."""
    try:
        return _hasher().verify(stored_hash, normalize_password(pw))
    except (argon2_exc.VerifyMismatchError, argon2_exc.InvalidHashError, argon2_exc.VerificationError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    """Parametrlər qaldırıldıqdan sonra köhnə hash yenilənməlidirmi (login-də rehash)."""
    try:
        return _hasher().check_needs_rehash(stored_hash)
    except argon2_exc.InvalidHashError:
        return False


# Timing-safe no-user yolu: təsadüfi parolun dummy hash-ı, import vaxtı bir dəfə.
# Login-də istifadəçi tapılmasa `verify_password(DUMMY_HASH, supplied)` çağırılır ki,
# "hesab var/yox" vaxt sızması olmasın. (§5)
DUMMY_HASH: str = _hasher().hash(secrets.token_urlsafe(32))


# ---- Token generasiya + hash (refresh / reset / verify / nonce) ----

def generate_token() -> str:
    """256-bit CSPRNG token (URL-safe). Xam dəyər yalnız istifadəçiyə verilir."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 hex (64 simvol). DB-də yalnız bu saxlanır."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
