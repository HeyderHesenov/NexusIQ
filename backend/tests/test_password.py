"""Argon2id parol hash + siyasət + token hash.

Kök səbəb / niyə: parol yolu auth-un ən çox istismar edilən səthidir. Bu testlər
Argon2id istifadəsini, rehash-on-login-i, siyasət sərhədlərini və NFKC-ni pinləyir.
"""
from __future__ import annotations

import pytest

from app.core import security
from app.core.config import settings
from app.core.security import PasswordPolicyError


@pytest.fixture(autouse=True)
def _fast_argon2(monkeypatch):
    # Testlərdə ucuz parametrlər (min: memory ≥ 8×parallelism).
    monkeypatch.setattr(settings, "argon2_time_cost", 1)
    monkeypatch.setattr(settings, "argon2_memory_kib", 64)
    monkeypatch.setattr(settings, "argon2_parallelism", 1)


def test_hash_verify_roundtrip():
    h = security.hash_password("correct horse battery")
    assert h.startswith("$argon2id$")
    assert security.verify_password(h, "correct horse battery") is True
    assert security.verify_password(h, "wrong password xxxx") is False


def test_hash_is_salted_unique():
    a = security.hash_password("same-password-123")
    b = security.hash_password("same-password-123")
    assert a != b  # salt fərqli → hash fərqli
    assert security.verify_password(a, "same-password-123")
    assert security.verify_password(b, "same-password-123")


def test_verify_bad_hash_returns_false():
    assert security.verify_password("not-a-valid-hash", "x") is False


def test_needs_rehash_after_raising_params(monkeypatch):
    h = security.hash_password("rehash-me-please")
    assert security.needs_rehash(h) is False
    monkeypatch.setattr(settings, "argon2_time_cost", 3)  # parametr qaldırıldı
    assert security.needs_rehash(h) is True


def test_policy_min_length():
    with pytest.raises(PasswordPolicyError) as e:
        security.validate_password("short")  # <12
    assert e.value.code == "password_too_short"


def test_policy_max_length():
    with pytest.raises(PasswordPolicyError) as e:
        security.validate_password("x" * 129)
    assert e.value.code == "password_too_long"


def test_policy_whitespace_only():
    with pytest.raises(PasswordPolicyError) as e:
        security.validate_password(" " * 14)
    assert e.value.code == "password_invalid"


def test_policy_accepts_valid():
    security.validate_password("twelvechars!")  # tam 12, keçir


def test_nfkc_normalization():
    # '①' NFKC-də '1'-ə çevrilir → fərqli təmsil, eyni normalizə parol.
    raw_a = "café-password-①"          # composed + circled digit
    raw_b = "café-password-1"      # decomposed é + plain 1
    h = security.hash_password(raw_a)
    assert security.verify_password(h, raw_b) is True


def test_dummy_hash_is_valid_argon2():
    assert security.DUMMY_HASH.startswith("$argon2id$")
    # No-user yolu: dummy-yə qarşı verify heç vaxt True verməməli (təsadüfi parol).
    assert security.verify_password(security.DUMMY_HASH, "anything") is False


def test_token_gen_and_hash():
    t1 = security.generate_token()
    t2 = security.generate_token()
    assert t1 != t2 and len(t1) >= 32
    h = security.hash_token(t1)
    assert len(h) == 64 and h == security.hash_token(t1)   # deterministik
    assert h != security.hash_token(t2)
