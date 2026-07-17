"""Təhlükəsizlik başlıqları — backend cavabları üçün (JSON API + şəkil proksisi).

Frontend-in öz başlıqları `next.config.mjs`-dədir; bura BACKEND-in birbaşa
verdiyi cavablara aiddir. Backend loopback-a bağlı olsa da bu başlıqlar publik
deploy üçün lazımdır və `dev.sh`-ın `/backend` rewrite-ı onsuz da bütün API-ni
frontend origin-i altından keçirir.

Qəsdən ETMƏDİKLƏRİM (hər biri real regresiya olardı):
- `Cache-Control: no-store` QOYULMUR: `/img/news/{id}` `FileResponse` ilə şəkil
  verir və keşlənməlidir (proksi məhz bunun üçün var). Route-lar öz
  `Cache-Control`-unu təyin edirsə ona toxunulmur.
- CSP `/docs` və `/openapi.json`-a TƏTBİQ OLUNMUR: Swagger UI inline skript və
  CDN işlədir; `default-src 'none'` onu dev-də sındırardı.
- HSTS default SÖNÜLÜDÜR: yalnız HTTPS arxasında məna daşıyır. Lokal HTTP-də
  brauzer onu iqnor etsə də, `localhost`-a yazılmış HSTS bütün lokal HTTP
  layihələrini sındıra bilər — ona görə açıq env qapısı ilə.
"""
from __future__ import annotations

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# JSON API üçün ən sərt CSP: heç nə yükləmə, çərçivəyə salınma.
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"

_STATIC_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), microphone=(), geolocation=(), interest-cohort=()",
    # Cavabı başqa origin-in oxumasını məhdudlaşdır (Spectre-vari sızmalara qarşı).
    # `same-site`, `same-origin` yox: `/backend` rewrite-ı Next serverindən keçir.
    "cross-origin-resource-policy": "same-site",
}

# CSP tətbiq OLUNMAYAN yollar (Swagger UI-ni sındırmamaq üçün).
_CSP_EXEMPT = ("/docs", "/openapi.json", "/redoc")


class SecurityHeaders:
    """Hər cavaba təhlükəsizlik başlıqları əlavə edir (mövcudları əzmir)."""

    def __init__(self, app: ASGIApp, *, hsts: bool = False) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        csp_ok = not path.startswith(_CSP_EXEMPT)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for k, v in _STATIC_HEADERS.items():
                    if k not in headers:
                        headers[k] = v
                if csp_ok and "content-security-policy" not in headers:
                    headers["content-security-policy"] = _API_CSP
                if self.hsts and "strict-transport-security" not in headers:
                    headers["strict-transport-security"] = (
                        "max-age=31536000; includeSubDomains"
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)
