"""clientip.client_ip — XFF spoofing qorunması.

Kök səbəb: köhnə kod `xff.split(",")[0]` (LEFTMOST) götürürdü — o giriş tam
hücumçu-nəzarətlidir (klient `X-Forwarded-For: 1.2.3.4` göndərir, hər proksi ONDAN
SONRA əlavə edir). Yeni model `trusted_proxy_hops` ilə rightmost-untrusted götürür.
Bu testlər hər iki klassik xətanı (leftmost trust + hops=0-da XFF-ə güvənmə) pinləyir.
"""
from __future__ import annotations

from types import SimpleNamespace

from app.core import clientip
from app.core.config import settings


class _Client:
    def __init__(self, host: str) -> None:
        self.host = host


def _req(xff=None, peer="9.9.9.9"):
    headers = {}
    if xff is not None:
        headers["x-forwarded-for"] = xff
    return SimpleNamespace(
        headers=headers,
        client=(_Client(peer) if peer else None),
        state=SimpleNamespace(),
    )


def test_hops0_ignores_xff(monkeypatch):
    # hops=0 → XFF tam iqnor, socket peer. (Cari default; spoofing bağlı.)
    monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
    assert clientip.client_ip(_req(xff="1.2.3.4", peer="9.9.9.9")) == "9.9.9.9"


def test_hops1_takes_rightmost_not_leftmost(monkeypatch):
    # hops=1 + "evil, 1.2.3.4" → 1.2.3.4 (NOT evil). Leftmost xətasının pini.
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    assert clientip.client_ip(_req(xff="evil, 1.2.3.4")) == "1.2.3.4"


def test_hops2_strips_two_trusted(monkeypatch):
    # hops=2 + 3 giriş → xff[-2].
    monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
    assert clientip.client_ip(_req(xff="1.1.1.1, 2.2.2.2, 3.3.3.3")) == "2.2.2.2"


def test_too_few_hops_falls_back_to_peer(monkeypatch):
    # len(xff) < hops → miskonfiqurasiya → peer.
    monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
    assert clientip.client_ip(_req(xff="1.2.3.4", peer="9.9.9.9")) == "9.9.9.9"


def test_non_ip_falls_back_to_peer(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    assert clientip.client_ip(_req(xff="not-an-ip", peer="9.9.9.9")) == "9.9.9.9"


def test_ipv4_port_stripped(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    assert clientip.client_ip(_req(xff="1.2.3.4:5678")) == "1.2.3.4"


def test_ipv6_bracket_port_stripped(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    assert clientip.client_ip(_req(xff="[2001:db8::1]:443")) == "2001:db8::1"


def test_no_client_returns_unknown(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 0)
    assert clientip.client_ip(_req(xff=None, peer=None)) == "unknown"


def test_hops1_no_xff_uses_peer(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    assert clientip.client_ip(_req(xff=None, peer="9.9.9.9")) == "9.9.9.9"
