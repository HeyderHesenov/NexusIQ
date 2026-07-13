"""SSRF qoruması — kənar (feed-mənbəli) URL-ləri çəkməzdən əvvəl host yoxlaması.

Naşir səhifələri və og:image URL-ləri RSS məzmunundan gəlir (attacker-adjacent).
Hostil bir element http://169.254.169.254 (cloud metadata), localhost və ya
RFC1918 daxili xidmətə yönəldə bilər. Bu köməkçi belə hədəfləri bloklayır və
redirect-ləri əl ilə, hər addımı yenidən yoxlayaraq izləyir.
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
    """Host adı/IP-si daxili şəbəkəyə işarə etmirsə True (DNS həll edərək)."""
    host = host.strip().lower().strip(".")
    if not host or host in _BLOCKED_HOSTS:
        return False
    if _is_blocked_ip(host):  # birbaşa IP literal
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    # Bütün həll olunmuş IP-lər ictimai olmalıdır (DNS rebinding qoruması).
    for info in infos:
        if _is_blocked_ip(info[4][0]):
            return False
    return True


async def is_safe_url(url: str) -> bool:
    """URL http/https-dir və host ictimai ünvana həll olunursa True."""
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
) -> httpx.Response | None:
    """SSRF-təhlükəsiz GET — redirect-ləri əl ilə izləyir, hər hopu yoxlayır.

    Client `follow_redirects=False` ilə yaradılmalıdır. Hər hansı hop daxili
    ünvana işarə edərsə None qaytarır (çəkilmir).
    """
    current = url
    for _ in range(max_redirects + 1):
        if not await is_safe_url(current):
            return None
        resp = await client.get(current, timeout=timeout)
        if resp.is_redirect and "location" in resp.headers:
            current = urljoin(current, resp.headers["location"])
            continue
        return resp
    return None  # çox redirect
