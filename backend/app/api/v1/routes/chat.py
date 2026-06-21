"""AI Asistant chat route — finance advisor (ikili AI debate + axın)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.advisor import answer, answer_stream
from app.db.session import AsyncSessionLocal, get_db

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    lang: str = "az"


class ChatResponse(BaseModel):
    answer: str
    refused: bool = False


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest, db: AsyncSession = Depends(get_db)
) -> ChatResponse:
    """İstifadəçi sualına maliyyə cavabı (arxa fonda debate)."""
    result = await answer(req.message, req.lang, db)
    return ChatResponse(**result)


@router.post("/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    """Axın cavabı (NDJSON) — qrafik + token-token yazılma effekti.

    Generator öz DB sessiyasını açır (StreamingResponse müddətincə açıq qalsın).
    """

    async def gen():
        async with AsyncSessionLocal() as session:
            async for event in answer_stream(req.message, req.lang, session):
                yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(
        gen(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
