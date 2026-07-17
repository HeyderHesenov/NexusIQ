"""Push abunəsi: SSRF qapısı + göndərmənin defolt thread hovuzunu tutmaması.

Kök səbəb (üç qüsur bir zəncir qurmuşdu):
1. `routes/push.py` endpoint-i YALNIZ `startswith("https://")` ilə yoxlayırdı —
   sxem daxili ünvan haqqında heç nə demir, yəni netguard yox idi. Anonim
   istifadəçi `https://169.254.169.254/...` qeydiyyatdan keçirə bilirdi və
   sonra SERVER ora POST edirdi (kor SSRF).
2. `_send_raw` `webpush()`-u timeout-suz çağırırdı. pywebpush-un `timeout=None`
   defoltu `send()`-ə AÇIQ ötürülür, `send()` isə `kwargs.pop("timeout", 10000)`
   edir — açar mövcud olduğu üçün pop 10000 fallback-ına çatmır, `None` qaytarır
   → `requests.post(timeout=None)` ƏBƏDİ bloklanır.
3. `send_to_all` limitsiz `asyncio.gather(*(asyncio.to_thread(...)))` edirdi —
   yəni DEFOLT hovuza (8 CPU → 12 işçi, `img_cache.py:58` ölçüb).

Birləşəndə: cavab verməyən ~12 abunə bütün defolt hovuzu əbədi tuturdu → hər
`asyncio.to_thread` (market, assets, correlation, radar, netguard DNS) növbəyə
düşürdü, `max_instances=1` isə ingest-i həmişəlik dayandırırdı. Restartsız bərpa
yox idi. Bu testlər hər üç halqanı ayrıca pinləyir — biri qırılsa da zəncir ölür.
"""
from __future__ import annotations

import asyncio
import socket
import threading

import httpx
import pytest
from fastapi import HTTPException

from app.api.v1.routes import push as push_route
from app.models import PushSubscription
from app.services import push_service


def _run(coro):
    return asyncio.run(coro)


def _sub(endpoint: str = "https://fcm.example.com/x") -> PushSubscription:
    return PushSubscription(endpoint=endpoint, p256dh="p", auth="a", lang="az")


# --- 1. SSRF qapısı -------------------------------------------------------


def test_internal_endpoint_rejected(monkeypatch):
    """Daxili ünvana həll olunan endpoint → 400 (siyasət verdikti)."""

    def private(*_a, **_kw):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", private)
    with pytest.raises(HTTPException) as exc:
        _run(push_route._assert_endpoint_safe("https://internal.example.com/push"))
    assert exc.value.status_code == 400


def test_metadata_ip_literal_rejected():
    """Cloud metadata IP literal-ı DNS-ə çıxmadan rədd edilir."""
    with pytest.raises(HTTPException) as exc:
        _run(push_route._assert_endpoint_safe("https://169.254.169.254/latest/meta"))
    assert exc.value.status_code == 400


def test_dns_failure_is_transient_not_policy(monkeypatch):
    """DNS nasazlığı → 503, 400 YOX.

    `netguard` bu ikisini qəsdən ayırır (bax test_netguard_dns.py): resolver
    blip-i "endpoint pisdir" demək deyil. 400 qaytarsaydıq brauzer abunəni
    həmişəlik yararsız sayardı.
    """

    def boom(*_a, **_kw):
        raise socket.gaierror(socket.EAI_AGAIN, "Temporary failure")

    monkeypatch.setattr(socket, "getaddrinfo", boom)
    with pytest.raises(HTTPException) as exc:
        _run(push_route._assert_endpoint_safe("https://fcm.googleapis.com/fcm/send/x"))
    assert exc.value.status_code == 503


def test_public_endpoint_allowed(monkeypatch):
    def public(*_a, **_kw):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", public)
    _run(push_route._assert_endpoint_safe("https://fcm.googleapis.com/fcm/send/x"))


# --- 2. webpush timeout ---------------------------------------------------


def test_webpush_called_with_finite_timeout(monkeypatch):
    """`webpush` SONLU timeout ilə çağırılmalıdır.

    pywebpush-un öz defoltu (`None`) `requests.post`-a düşür və əbədi bloklayır —
    ona görə timeout-u AÇIQ ötürməyimiz vacibdir, susmaq fallback-a çatmır.
    """
    seen: dict = {}

    def spy(**kwargs):
        seen.update(kwargs)

    monkeypatch.setattr(push_service, "webpush", spy)
    assert push_service._send_raw(_sub(), {"title": "x"}) is None
    assert isinstance(seen.get("timeout"), (int, float))
    assert 0 < seen["timeout"] < 60


def test_send_raw_swallows_network_error(monkeypatch):
    """Timeout/şəbəkə xətası bir abunəni öldürsün, bütün dalğanı yox."""

    def boom(**_kw):
        raise httpx.ConnectError("timed out")

    monkeypatch.setattr(push_service, "webpush", boom)
    assert push_service._send_raw(_sub(), {"title": "x"}) is None


# --- 3. Hovuz izolyasiyası + paralellik tavanı ----------------------------


def test_send_runs_off_the_default_thread_pool(monkeypatch):
    """Göndərmə AYRICA hovuzda işləməlidir — defolt hovuz toxunulmaz qalsın.

    Defolt hovuz yfinance çağırışları ilə paylaşılır; bloklanan push onu tutsa
    bütün app dayanır. Thread adı hovuz kimliyini sübut edir.
    """
    names: list[str] = []

    def spy(**_kw):
        names.append(threading.current_thread().name)

    monkeypatch.setattr(push_service, "webpush", spy)
    _run(push_service._send_one(_sub(), {"title": "x"}))
    assert names and all(n.startswith("webpush") for n in names)


def test_fanout_concurrency_is_bounded(monkeypatch):
    """Limitsiz fan-out bağlanıb: eyni anda işləyən göndərmə sayı tavanlıdır."""
    lock = threading.Lock()
    live = 0
    peak = 0

    def spy(**_kw):
        nonlocal live, peak
        with lock:
            live += 1
            peak = max(peak, live)
        try:
            import time

            time.sleep(0.02)
        finally:
            with lock:
                live -= 1

    monkeypatch.setattr(push_service, "webpush", spy)

    async def fan():
        await asyncio.gather(
            *(push_service._send_one(_sub(), {"title": "x"}) for _ in range(40))
        )

    _run(fan())
    assert peak <= push_service._POOL._max_workers
