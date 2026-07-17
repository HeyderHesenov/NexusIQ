"""v1 API router aqreqatoru. Hər modul öz route faylını bura qoşur."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.routes import (
    accuracy,
    analog,
    anomalies,
    assets,
    auth,
    chat,
    correlation,
    health,
    img,
    market,
    me,
    news,
    push,
    radar,
    watchlist_intel,
)
from app.core.auth import require_user

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# /me/* tam USER — router səviyyəsində require_user (heç bir route unuda bilməz).
api_router.include_router(
    me.router, prefix="/me", tags=["me"], dependencies=[Depends(require_user)]
)
api_router.include_router(news.router, prefix="/news", tags=["news"])
api_router.include_router(chat.router, prefix="/chat", tags=["advisor"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(push.router, prefix="/push", tags=["push"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(img.router, prefix="/img", tags=["news"])
api_router.include_router(
    anomalies.router, prefix="/anomalies", tags=["analytics"]
)
api_router.include_router(
    correlation.router, prefix="/correlation", tags=["analytics"]
)
api_router.include_router(radar.router, prefix="/radar", tags=["analytics"])
api_router.include_router(analog.router, prefix="/analogs", tags=["analytics"])
api_router.include_router(
    watchlist_intel.router, prefix="/watchlist-intel", tags=["analytics"]
)
api_router.include_router(accuracy.router, prefix="/accuracy", tags=["analytics"])
