"""`summarize_ai._fetch_context` kənar URL-ləri netguard-dan keçirməlidir.

Kök səbəb: bu funksiya xam `client.get(url)` edirdi — netguard YOX, üstəlik klient
`follow_redirects=True` ilə qurulurdu və bayt tavanı yox idi (`r.text[:300_000]`
TAM yükləmədən SONRA kəsir → yaddaşı qorumur).

`url` RSS-dən gəlir (attacker-adjacent). Qardaş modulların hamısı — `img_cache`,
`enrich_content`, `enrich_images` — eyni etibar səviyyəli URL-lər üçün
`netguard.safe_get` işlədir; yalnız bu modul qapıdan kənarda qalmışdı.

Ən pisi: bu yol KOR DEYİL. Çəkilən gövdə parse olunur → LLM-ə verilir →
`News.summary`-yə yazılır → `GET /news`-də PUBLİK verilir. Yəni daxili xidmətdən
oxunan məzmun birbaşa eksfiltrasiya olunurdu. (netguard docstring-i "enrich_content
body-ni parse etdiyi üçün orada rebinding kor deyil" deyir — amma enrich_content
guard-DAN İSTİFADƏ EDİR; qorunmayan parser məhz bu modul idi.)
"""
from __future__ import annotations

import asyncio
import socket

import httpx
import pytest

from app.agents import summarize_ai


def _run(coro):
    return asyncio.run(coro)


_HTML = (
    '<html><meta property="og:description" content="'
    + "Bazar xəbəri konteksti burada yerləşir və kifayət qədər uzundur. " * 2
    + '"></html>'
)


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_internal_host_not_fetched(monkeypatch):
    """Daxili ünvana həll olunan host → çəkiliş HEÇ BAŞLAMIR, boş kontekst."""
    hits: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hits.append(str(request.url))
        return httpx.Response(200, text=_HTML)

    def private(*_a, **_kw):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", private)

    async def go():
        async with _client(handler) as cli:
            return await summarize_ai._fetch_context(cli, "https://internal.example.com/a")

    assert _run(go()) == ""
    assert hits == [], "netguard-dan keçmədən daxili hosta sorğu getdi"


def test_metadata_ip_literal_not_fetched():
    """Cloud metadata IP literal-ı DNS-siz bloklanır."""
    hits: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hits.append(str(request.url))
        return httpx.Response(200, text=_HTML)

    async def go():
        async with _client(handler) as cli:
            return await summarize_ai._fetch_context(
                cli, "http://169.254.169.254/latest/meta-data/"
            )

    assert _run(go()) == ""
    assert hits == []


def test_redirect_to_internal_blocked(monkeypatch):
    """İctimai host DAXİLİ ünvana yönləndirsə ikinci hop çəkilməməlidir.

    Məhz buna görə klient `follow_redirects=False` olmalıdır: httpx-in öz
    izləməsi hopları yoxlamır, netguard isə hər hopu yenidən yoxlayır.
    """
    hits: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hits.append(request.url.host)
        if request.url.host == "public.example.com":
            return httpx.Response(302, headers={"location": "http://10.0.0.5/secret"})
        return httpx.Response(200, text=_HTML)

    def resolve(host, *_a, **_kw):
        ip = "93.184.216.34" if host == "public.example.com" else "10.0.0.5"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)

    async def go():
        async with _client(handler) as cli:
            return await summarize_ai._fetch_context(cli, "https://public.example.com/a")

    assert _run(go()) == ""
    assert "10.0.0.5" not in hits, "daxili hopa sorğu getdi — redirect yoxlanmayıb"


def test_public_host_still_works(monkeypatch):
    """Real naşir hələ də çəkilir — guard legitim yolu qırmır."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_HTML)

    def public(*_a, **_kw):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", public)

    async def go():
        async with _client(handler) as cli:
            return await summarize_ai._fetch_context(cli, "https://news.example.com/a")

    assert "Bazar xəbəri konteksti" in _run(go())


def test_production_client_does_not_follow_redirects():
    """PRODUKSİYA klienti `follow_redirects=False` ilə qurulmalıdır.

    Bu ayrıca pinlənir, çünki yuxarıdakı hop testi öz klientini qurur və
    produksiya konfiqini əks etdirmir. netguard redirect-ləri ƏL İLƏ, hər hopu
    yenidən yoxlayaraq izləyir — httpx özü izləsə hoplar yoxlanmadan keçər və
    guard tamamilə yan keçilər. `safe_get` docstring-i bunu tələb edir.
    """
    import inspect

    src = inspect.getsource(summarize_ai.summarize_pending)
    assert "follow_redirects=False" in src
    assert "follow_redirects=True" not in src


def test_oversized_body_capped(monkeypatch):
    """Tavanı aşan gövdə → boş kontekst (axın kəsilir, yaddaşa yığılmır)."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * (summarize_ai._MAX_FETCH_BYTES + 1024))

    def public(*_a, **_kw):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", public)

    async def go():
        async with _client(handler) as cli:
            return await summarize_ai._fetch_context(cli, "https://news.example.com/big")

    assert _run(go()) == ""
