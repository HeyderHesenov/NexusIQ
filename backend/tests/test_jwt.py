"""HS256 access token — klassik JWT qətlləri pinlənir.

Kök səbəb: JWT-nin iki məşhur boşluğu (1) alg confusion / alg:none — decode
başlıqdakı alg-a güvənəndə, (2) token-type confusion — refresh token access kimi
qəbul olunanda. Hər ikisi burada açıq test kimi bağlanır.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest

from app.core import jwtsvc
from app.core.config import settings

_SECRET = "test-secret-that-is-long-enough-32chars-min-000"


@pytest.fixture(autouse=True)
def _known_secret(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", _SECRET)
    monkeypatch.setattr(settings, "jwt_secret_previous", "")
    monkeypatch.setattr(settings, "jwt_issuer", "nexusiq")
    monkeypatch.setattr(settings, "jwt_audience", "nexusiq")
    monkeypatch.setattr(settings, "access_ttl_seconds", 600)


def _craft(overrides=None, secret=_SECRET, alg="HS256"):
    now = datetime.now(timezone.utc)
    base = {
        "sub": "user-1", "sid": "sess-1", "typ": "access", "tv": 0,
        "iat": now, "exp": now + timedelta(minutes=5),
        "iss": "nexusiq", "aud": "nexusiq",
    }
    if overrides:
        base.update(overrides)
    return pyjwt.encode(base, secret, algorithm=alg)


def test_roundtrip():
    tok = jwtsvc.mint_access("user-1", "sess-1", tv=123)
    claims = jwtsvc.decode_access(tok)
    assert claims["sub"] == "user-1" and claims["sid"] == "sess-1"
    assert claims["typ"] == "access" and claims["tv"] == 123


def test_alg_none_rejected():
    tok = pyjwt.encode({"sub": "x", "sid": "y", "typ": "access", "tv": 0,
                        "iat": datetime.now(timezone.utc),
                        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
                        "iss": "nexusiq", "aud": "nexusiq"}, "", algorithm="none")
    with pytest.raises(pyjwt.InvalidTokenError):
        jwtsvc.decode_access(tok)


def test_alg_confusion_rs256_rejected():
    # RS256 ilə imzalanmış token — algorithms=["HS256"] pinlənib → InvalidAlgorithmError.
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(timezone.utc)
    tok = pyjwt.encode(
        {"sub": "x", "sid": "y", "typ": "access", "tv": 0, "iat": now,
         "exp": now + timedelta(minutes=5), "iss": "nexusiq", "aud": "nexusiq"},
        key, algorithm="RS256",
    )
    with pytest.raises(pyjwt.InvalidTokenError):
        jwtsvc.decode_access(tok)


def test_wrong_secret_rejected():
    tok = _craft(secret="a-totally-different-wrong-secret-value-000")
    with pytest.raises(pyjwt.InvalidTokenError):
        jwtsvc.decode_access(tok)


def test_expired_raises_expired():
    tok = _craft({"exp": datetime.now(timezone.utc) - timedelta(seconds=10)})
    with pytest.raises(pyjwt.ExpiredSignatureError):
        jwtsvc.decode_access(tok)


def test_wrong_audience_rejected():
    tok = _craft({"aud": "someone-else"})
    with pytest.raises(pyjwt.InvalidTokenError):
        jwtsvc.decode_access(tok)


def test_wrong_issuer_rejected():
    tok = _craft({"iss": "evil-issuer"})
    with pytest.raises(pyjwt.InvalidTokenError):
        jwtsvc.decode_access(tok)


def test_missing_claim_rejected():
    # `sid` olmadan → MissingRequiredClaimError (require siyahısı).
    now = datetime.now(timezone.utc)
    tok = pyjwt.encode({"sub": "x", "typ": "access", "tv": 0, "iat": now,
                        "exp": now + timedelta(minutes=5), "iss": "nexusiq",
                        "aud": "nexusiq"}, _SECRET, algorithm="HS256")
    with pytest.raises(pyjwt.InvalidTokenError):
        jwtsvc.decode_access(tok)


def test_typ_refresh_rejected():
    # typ='refresh' access kimi təqdim → rədd (token-type confusion).
    tok = _craft({"typ": "refresh"})
    with pytest.raises(pyjwt.InvalidTokenError):
        jwtsvc.decode_access(tok)


def test_previous_secret_accepted_random_rejected(monkeypatch):
    # OLD ilə imzalanmış token, rotasiyadan sonra (current=NEW, previous=OLD) qəbul.
    old = _SECRET
    tok = _craft(secret=old)
    monkeypatch.setattr(settings, "jwt_secret", "new-secret-after-rotation-32chars-min-00")
    monkeypatch.setattr(settings, "jwt_secret_previous", old)
    assert jwtsvc.decode_access(tok)["sub"] == "user-1"
    # Nə current, nə previous ilə uyğun olmayan random secret → rədd.
    bad = _craft(secret="random-unrelated-secret-not-current-or-prev")
    with pytest.raises(pyjwt.InvalidTokenError):
        jwtsvc.decode_access(bad)
