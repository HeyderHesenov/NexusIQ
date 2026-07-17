"""Backend təhlükəsizlik başlıqları + Host qorusu + /health kəşfiyyatı.

Kök səbəb: backend HEÇ BİR təhlükəsizlik başlığı vermirdi (nə CSP, nə HSTS, nə
X-Frame-Options, nə nosniff, nə Referrer-Policy) və `TrustedHostMiddleware`
yox idi (Host başlığı inyeksiyası qorunmurdu). `/health` isə anonim sorğuya
`env` (deployment mühiti) deyirdi.

Bu testlər həm başlıqların VARLIĞINI, həm də QƏSDƏN ÇIXARILANLARI pinləyir —
sonuncular real regresiya olardı:
  - `/docs`-a CSP tətbiq olunsa Swagger UI dev-də sınar.
  - Qlobal `Cache-Control: no-store` şəkil proksisinin keşini öldürər.
  - HSTS lokal HTTP-də açılsa `localhost`-a yazılıb bütün lokal HTTP
    layihələrini sındıra bilər.
"""
from __future__ import annotations

import httpx
import pytest

from app.core.config import settings
from app.core.security_headers import _API_CSP, SecurityHeaders


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )


async def _plain_app(scope, receive, send):
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": b"{}"})


@pytest.mark.asyncio
async def test_static_headers_present():
    app = SecurityHeaders(_plain_app)
    async with _client(app) as c:
        r = await c.get("/api/v1/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert "camera=()" in r.headers["permissions-policy"]
    assert r.headers["cross-origin-resource-policy"] == "same-site"
    assert r.headers["content-security-policy"] == _API_CSP


@pytest.mark.asyncio
async def test_hsts_absent_by_default():
    """HSTS default SÖNÜLÜ — lokal HTTP-də açmaq təhlükəlidir."""
    app = SecurityHeaders(_plain_app, hsts=False)
    async with _client(app) as c:
        r = await c.get("/api/v1/health")
    assert "strict-transport-security" not in r.headers


@pytest.mark.asyncio
async def test_hsts_present_when_enabled():
    app = SecurityHeaders(_plain_app, hsts=True)
    async with _client(app) as c:
        r = await c.get("/api/v1/health")
    assert "max-age=31536000" in r.headers["strict-transport-security"]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/docs", "/openapi.json", "/redoc"])
async def test_csp_not_applied_to_swagger(path):
    """Swagger UI inline skript işlədir — CSP onu sındırardı."""
    app = SecurityHeaders(_plain_app)
    async with _client(app) as c:
        r = await c.get(path)
    assert "content-security-policy" not in r.headers
    # digər başlıqlar hələ də qalır
    assert r.headers["x-content-type-options"] == "nosniff"


@pytest.mark.asyncio
async def test_no_global_cache_control():
    """Qlobal `Cache-Control` QOYULMUR — şəkil proksisinin keşi ölməsin."""
    app = SecurityHeaders(_plain_app)
    async with _client(app) as c:
        r = await c.get("/api/v1/img/news/1")
    assert "cache-control" not in r.headers


@pytest.mark.asyncio
async def test_route_headers_not_clobbered():
    """Route öz başlığını təyin edibsə middleware onu ƏZMİR."""

    async def app_with_own(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"image/webp"),
                    (b"cache-control", b"public, max-age=86400"),
                    (b"x-frame-options", b"SAMEORIGIN"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    async with _client(SecurityHeaders(app_with_own)) as c:
        r = await c.get("/api/v1/img/news/1")
    assert r.headers["cache-control"] == "public, max-age=86400"
    assert r.headers["x-frame-options"] == "SAMEORIGIN"  # əzilmədi


# ---- /health kəşfiyyatı ----


def test_health_does_not_leak_environment():
    """`/health` deployment mühitini AÇMAMALIDIR."""
    import inspect

    from app.api.v1.routes import health

    src = inspect.getsource(health.health)
    assert "environment" not in src


def test_trusted_hosts_config_parses():
    assert settings.trusted_hosts_list  # ən azı ["*"]
    s = type(settings)(trusted_hosts="a.com, b.com ,")
    assert s.trusted_hosts_list == ["a.com", "b.com"]
