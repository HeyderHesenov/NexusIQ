"""NexusIQ FastAPI giriş nöqtəsi."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.scheduler import shutdown_scheduler, start_scheduler, startup_catchup

logger = logging.getLogger("nexusiq.startup")

_IS_DEV = settings.environment == "development"
_MAX_BODY = 256 * 1024  # 256 KB — sorğu gövdəsi limiti (DoS/yaddaş qoruması)


class _BodySizeLimit:
    """Sorğu gövdəsi həddini aşan POST/PUT/PATCH-i 413 ilə rədd edir.

    Content-Length-i yoxlamaqla kifayətlənmir — `Transfer-Encoding: chunked`
    (Content-Length-siz) bypass-ını da bağlamaq üçün gövdəni oxuyaraq baytları
    sayır. Kiçik JSON gövdələri buferlənib downstream-ə yenidən ötürülür.
    """

    def __init__(self, app, max_body: int = _MAX_BODY) -> None:
        self.app = app
        self.max_body = max_body

    async def __call__(self, scope, receive, send):
        if scope.get("type") != "http" or scope.get("method") not in (
            "POST",
            "PUT",
            "PATCH",
        ):
            await self.app(scope, receive, send)
            return

        # Content-Length varsa erkən rədd — gövdəni heç oxumadan.
        for name, value in scope.get("headers", []):
            if name == b"content-length" and value.isdigit():
                if int(value) > self.max_body:
                    await self._too_large(scope, receive, send)
                    return
                break

        # Gövdəni həddə qədər buferlə (chunked/Content-Length-siz üçün də).
        buffered: list[dict] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                buffered.append(message)
                break
            total += len(message.get("body", b""))
            if total > self.max_body:
                await self._too_large(scope, receive, send)
                return
            buffered.append(message)
            if not message.get("more_body", False):
                break

        sent = False

        async def replay():
            nonlocal sent
            if buffered:
                return buffered.pop(0)
            sent = True
            return await receive()

        await self.app(scope, replay, send)

    async def _too_large(self, scope, receive, send) -> None:
        resp = JSONResponse(
            {"detail": "Sorğu gövdəsi çox böyükdür."}, status_code=413
        )
        await resp(scope, receive, send)


async def _prewarm() -> None:
    """Ağır analitik keşləri arxa planda isidir — ilk istifadəçi gözləməsin."""
    from app.analytics import anomaly, assets, correlation, market, radar

    tasks = {
        "market": market.get_quotes(),
        "metals": market.get_metals(),
        "commodities": market.get_commodities(),
        "overview": assets.get_overview(),
        "correlation": correlation.get_matrix(90),
        "anomaly": anomaly.scan_all(),
        "radar_crypto": radar.get_radar("crypto"),
        "radar_stock": radar.get_radar("stock"),
        "radar_commodity": radar.get_radar("commodity"),
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    warmed = [n for n, r in zip(tasks, results) if not isinstance(r, Exception)]
    logger.info("Prewarm tamamlandı: %s", ", ".join(warmed) or "yox")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Başlanğıc / bağlanış hadisələri — planlayıcı + keş istiləşməsi."""
    # startup
    start_scheduler()
    asyncio.create_task(_prewarm())  # blok etmədən keşləri isidir
    asyncio.create_task(startup_catchup())  # tərcüməsiz backlog-u dərhal tut
    yield
    # shutdown
    shutdown_scheduler()


def create_app() -> FastAPI:
    # Swagger/OpenAPI yalnız development-də açıq (prod-da API səthi gizli).
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Financial Intelligence Platform — AI Analyst Terminal",
        lifespan=lifespan,
        docs_url="/docs" if _IS_DEV else None,
        redoc_url=None,
        openapi_url="/openapi.json" if _IS_DEV else None,
    )

    app.add_middleware(_BodySizeLimit)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,  # frontend cookie/credential göndərmir
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/")
    async def root() -> dict:
        info = {"app": settings.app_name, "api": settings.api_v1_prefix}
        if _IS_DEV:
            info["docs"] = "/docs"
        return info

    return app


app = create_app()
