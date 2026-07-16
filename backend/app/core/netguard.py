"""SSRF qoruması — kənar (feed-mənbəli) URL-ləri çəkməzdən əvvəl host yoxlaması.

Naşir səhifələri və og:image URL-ləri RSS məzmunundan gəlir (attacker-adjacent).
Hostil bir element http://169.254.169.254 (cloud metadata), localhost və ya
RFC1918 daxili xidmətə yönəldə bilər. Bu köməkçi belə hədəfləri bloklayır və
redirect-ləri əl ilə, hər addımı yenidən yoxlayaraq izləyir.

Yoxlama HƏLL OLUNMUŞ ünvanlar üzərindədir (giriş sətri üzərində yox) — onluq/
səkkizlik IP kodlaşdırmaları, IPv4-mapped IPv6 və çox-A qeydləri bununla birdən
bağlanır (`getaddrinfo` kanonikləşdirir, sonra HƏR nəticə yoxlanır).

BİLİNƏN QALIQ RİSK — DNS rebinding (TOCTOU): `_host_is_safe` `getaddrinfo` çağırır,
sonra httpx hostu MÜSTƏQİL olaraq YENİDƏN həll edir; təsdiqlənmiş IP ötürülmür.
TTL=0 ilə authoritative DNS işlədən hücumçu iki həll arasında daxili ünvana keçə
bilər. Tam həll IP-ni pinləmək (URL-də IP + `Host` başlığı + `sni_hostname`)
olardı; tətbiq edilmədi, çünki sertifikat yoxlanışını qırma riski real naşirlər
üçün bütün şəkilləri sındıra bilər. Cari azaldıcılar: (1) `/img/news/{id}` yolunda
SSRF KORDUR — cavab Pillow-dan keçməlidir, metadata JSON `UnidentifiedImageError`
verir; (2) tək plain-HTTP feed HTTPS-ə keçirildi (bax `sources.py` MarketWatch),
yəni DB-yə ixtiyari URL yeritmək üçün on-path mövqe artıq kifayət etmir;
(3) app 127.0.0.1-ə bağlıdır. Qalan kanal: yan-təsirli GET və vaxt oraklu.
`enrich_content` body-ni PARSE etdiyi üçün orada rebinding kor DEYİL.
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

_BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "metadata"}


def _is_blocked_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _host_is_safe(host: str) -> bool:
    """Host adı/IP-si daxili şəbəkəyə işarə etmirsə True (DNS həll edərək).

    DNS-in ÖZÜ alınmasa `httpx.ConnectError` qaldırılır — `False` QAYTARILMIR.
    `False` "bu host qadağandır" deməkdir (siyasət verdikti, host dəyişməyincə
    dəyişməz); resolver nasazlığı isə keçici I/O xətasıdır. İkisini eyni dəyərə
    yığmaq realdır və ağırdır: şəbəkə bir anlıq gedəndə HƏR host "qadağan"
    görünür, çağıranlar isə bunu davamlı verdikt kimi yazır (`img_cache` neqativ
    keşi: 15 dəq) → şəbəkə qayıdandan sonra da bütün şəkillər örtük altında
    qalır. Eyni kök şərt TCP mərhələsində düzgün işlənirdi (`client.get` →
    `ConnectError` → keçici), yalnız DNS yolu fərqlənirdi.

    Məhz `ConnectError`, çünki biz httpx-in öz həllini ƏVƏZ edirik — o, hostu
    özü həll etsəydi DNS xətasında elə bunu qaldırardı. Nəticədə hər üç çağıran
    onu artıq düzgün tutur, imza dəyişmir.
    NXDOMAIN də bura düşür (ayırd edilmir): errno platformadan asılıdır (macOS
    oflayn ikən EAI_NONAME/EAI_NODATA verir), qiyməti isə cəmi resolver-in öz
    neqativ keşinə 90 saniyədən bir dəyməkdir — naşirə sorğu getmir.
    Təhlükəsizlik dəyişmir: istisna da çəkilişi dayandırır (fail-closed).
    """
    host = host.strip().lower().strip(".")
    if not host or host in _BLOCKED_HOSTS:
        return False
    if _is_blocked_ip(host):  # birbaşa IP literal
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise httpx.ConnectError(f"DNS həlli alınmadı: {host}") from exc
    # Bütün həll olunmuş IP-lər ictimai olmalıdır (DNS rebinding qoruması).
    for info in infos:
        if _is_blocked_ip(info[4][0]):
            return False
    return True


async def is_safe_url(url: str) -> bool:
    """URL http/https-dir və host ictimai ünvana həll olunursa True.

    DNS həlli alınmasa `httpx.ConnectError` qaldırır (səbəb: `_host_is_safe`).
    """
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    # DNS həlli bloklayır → thread-ə ver.
    return await asyncio.to_thread(_host_is_safe, parsed.hostname)


async def safe_get(
    client: httpx.AsyncClient,
    url: str,
    *,
    timeout: float = 15.0,
    max_redirects: int = 8,
    max_bytes: int | None = None,
) -> httpx.Response | None:
    """SSRF-təhlükəsiz GET — redirect-ləri əl ilə izləyir, hər hopu yoxlayır.

    Client `follow_redirects=False` ilə yaradılmalıdır.

    `None` = SİYASƏT verdikti, yəni "çəkməkdən imtina": qadağan host/hop, `max_bytes`
    tavanının aşılması, həddindən çox redirect. Bu hallar URL dəyişməyincə dəyişməz,
    ona görə çağıran onları uzun müddət keşləyə bilər.
    I/O nasazlıqları (DNS, TCP, TLS, timeout) `None` DEYİL — httpx istisnası kimi
    sıçrayır, çünki onlar keçicidir və başqa cür işlənməlidir.

    `max_bytes` verilsə cavab AXINLA oxunur və tavan aşılan kimi bağlanır.
    Bu vacibdir: `client.get()` body-ni TAM yaddaşa yığır və httpx-in ölçü
    limiti YOXDUR — yükləmədən sonrakı `len(r.content)` yoxlaması yaddaşı
    qorumur, yalnız emalın qarşısını alır. None (defolt) = köhnə davranış.
    """
    current = url
    for _ in range(max_redirects + 1):
        if not await is_safe_url(current):
            return None
        if max_bytes is None:
            resp = await client.get(current, timeout=timeout)
        else:
            resp = await _capped_get(client, current, timeout, max_bytes)
            if resp is None:
                return None  # tavan aşıldı
        if resp.is_redirect and "location" in resp.headers:
            current = urljoin(current, resp.headers["location"])
            continue
        return resp
    return None  # çox redirect


async def _capped_get(
    client: httpx.AsyncClient, url: str, timeout: float, max_bytes: int
) -> httpx.Response | None:
    """Axınla oxu, `max_bytes` aşılanda bağla. Buferlənmiş cavabı qaytarır."""
    req = client.build_request("GET", url, timeout=timeout)
    resp = await client.send(req, stream=True)
    try:
        if resp.is_redirect:
            return resp  # body lazım deyil, çağıran Location-a baxır
        chunks: list[bytes] = []
        total = 0
        # `aiter_bytes` AÇILMIŞ baytları verir → tavan yaddaşda tutduğumuza
        # tətbiq olunur (gzip bombası da elə burada kəsilir).
        async for chunk in resp.aiter_bytes():
            total += len(chunk)
            if total > max_bytes:
                return None
            chunks.append(chunk)
        body = b"".join(chunks)
    finally:
        await resp.aclose()
    # Axın bağlandıqdan sonra `.content`/`.text` oxunmur → buferlənmiş nüsxə qur.
    # Body ARTIQ açılıb, ona görə kodlaşdırma başlıqları çıxarılmalıdır: qalsa
    # httpx yeni cavabı ikinci dəfə açmağa çalışır → DecodingError.
    headers = httpx.Headers(resp.headers)
    headers.pop("content-encoding", None)
    headers.pop("content-length", None)
    return httpx.Response(
        status_code=resp.status_code,
        headers=headers,
        content=body,
        request=resp.request,
    )
