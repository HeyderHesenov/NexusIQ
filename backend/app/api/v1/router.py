"""v1 API router aqreqatoru. Hər modul öz route faylını bura qoşur."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import health

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])

# Növbəti addımlarda qoşulacaq:
# api_router.include_router(news.router, prefix="/news", tags=["news"])
# api_router.include_router(chat.router, prefix="/chat", tags=["advisor"])
# api_router.include_router(correlation.router, prefix="/correlation", tags=["analytics"])
