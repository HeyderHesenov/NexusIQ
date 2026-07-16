"""`netguard` — DNS nasazlığı ilə "qadağan host" verdikti qarışmamalıdır.

Kök səbəb (ölçüldü): `_host_is_safe` `socket.gaierror`-u udub `False` qaytarırdı,
`safe_get` isə buna görə `None` verirdi — yəni "bu host qadağandır" ilə eyni dəyər.
`img_cache` `None`-u davamlı verdikt sayıb 15 dəqiqəlik neqativ keş yazırdı, ona görə
bir anlıq resolver/şəbəkə nasazlığı BÜTÜN şəkilləri (hər host eyni anda) şəbəkə
qayıtdıqdan sonra da örtük altında saxlayırdı. Eyni kök şərt TCP mərhələsində düzgün
işlənirdi — yalnız DNS yolu fərqlənirdi.
"""
from __future__ import annotations

import asyncio
import socket

import httpx
import pytest

from app.core import netguard


def _run(coro):
    return asyncio.run(coro)


def test_dns_failure_raises_connect_error(monkeypatch):
    """DNS alınmasa → `httpx.ConnectError` (keçici), sakit `False` YOX."""

    def boom(*_a, **_kw):
        raise socket.gaierror(socket.EAI_NONAME, "nodename nor servname provided")

    monkeypatch.setattr(socket, "getaddrinfo", boom)
    with pytest.raises(httpx.ConnectError):
        _run(netguard.is_safe_url("https://example.com/a.jpg"))


def test_blocked_host_still_returns_false(monkeypatch):
    """Siyasət verdikti dəyişməyib: daxili ünvana həll olunan host → False."""

    def private(*_a, **_kw):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", private)
    assert _run(netguard.is_safe_url("https://internal.example.com/a.jpg")) is False


def test_ip_literal_blocked_without_dns():
    """Loopback literal DNS-ə çıxmadan bloklanır — istisna deyil, verdikt."""
    assert _run(netguard.is_safe_url("http://127.0.0.1:8001/x.jpg")) is False


def test_public_host_allowed(monkeypatch):
    def public(*_a, **_kw):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", public)
    assert _run(netguard.is_safe_url("https://example.com/a.jpg")) is True


def test_img_cache_classifies_dns_failure_as_transient(monkeypatch):
    """Bütöv zəncir: DNS nasazlığı → QISA (soft) neqativ keş, uzun yox.

    Bu testin qoruduğu regresiya elə buradadır: `_fetch` istisnanı tutub
    `transient=True` deməlidir, `safe_get`-in `None`-u ilə eyni yola düşməməlidir.
    """
    import time

    from app.services import img_cache

    def boom(*_a, **_kw):
        raise socket.gaierror(socket.EAI_AGAIN, "Temporary failure in name resolution")

    monkeypatch.setattr(socket, "getaddrinfo", boom)
    img_cache._neg.clear()

    url = "https://cdn.example.com/foto.jpg"
    assert _run(img_cache.get_path(424242, url, 192)) is None
    ttl = img_cache._neg[img_cache._key(424242, url, 192)] - time.monotonic()
    assert ttl <= img_cache._NEG_TTL_SOFT
    img_cache._neg.clear()


def test_img_cache_policy_verdict_is_hard(monkeypatch):
    """Qadağan host (siyasət) → UZUN (hard) neqativ keş."""
    import time

    from app.services import img_cache

    def private(*_a, **_kw):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", private)
    img_cache._neg.clear()

    url = "https://internal.example.com/foto.jpg"
    assert _run(img_cache.get_path(424243, url, 192)) is None
    ttl = img_cache._neg[img_cache._key(424243, url, 192)] - time.monotonic()
    assert ttl > img_cache._NEG_TTL_SOFT
    img_cache._neg.clear()
