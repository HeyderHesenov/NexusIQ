"""NexusIQ FastAPI giriş nöqtəsi."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.scheduler import shutdown_scheduler, start_scheduler

logger = logging.getLogger("nexusiq.startup")


async def _prewarm() -> None:
    """Ağır analitik keşləri arxa planda isidir — ilk istifadəçi gözləməsin."""
    from app.analytics import anomaly, assets, correlation, market

    tasks = {
        "market": market.get_quotes(),
        "metals": market.get_metals(),
        "commodities": market.get_commodities(),
        "overview": assets.get_overview(),
        "correlation": correlation.get_matrix(90),
        "anomaly": anomaly.scan_all(),
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
    yield
    # shutdown
    shutdown_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Financial Intelligence Platform — AI Analyst Terminal",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/")
    async def root() -> dict:
        return {"app": settings.app_name, "docs": "/docs", "api": settings.api_v1_prefix}

    return app


app = create_app()
