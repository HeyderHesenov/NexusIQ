"""AI Asistant chat route — grounded finance advisor (debate + canlı data + axın)."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.advisor import answer, answer_stream
from app.core.auth import require_user
from app.core.ratelimit import rate_limit
from app.db.session import AsyncSessionLocal, get_db
from app.models import User
from app.services import user_data

router = APIRouter()

# bahalı LLM çağırışları — per-IP məhdudiyyət (cost/DoS qoruması)
_chat_limit = rate_limit("chat", limit=30, window=60.0)


class ChatTurn(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    lang: str = "az"
    # Çoxaddımlı yaddaş — son növbələr (follow-up konteksti). Sərhədli: xərc idarəli.
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)


class ChatResponse(BaseModel):
    answer: str
    refused: bool = False


async def _load_personal(session: AsyncSession, user_id) -> tuple[list, list, object]:
    """İstifadəçinin holdings + watchlist + last_seen — grounded şəxsi cavab üçün.

    Ucuz, per-user indeksli oxular. Advisor bunları yalnız plan istəyəndə işlədir
    (`portfolio`/`watchlist` siqnalı) — burada sadəcə hazır saxlanır.
    """
    rows = await user_data.list_holdings(session, user_id)
    holdings = [
        {
            "key": h.asset_key,
            "qty": float(h.qty),
            "avgCost": float(h.avg_cost) if h.avg_cost is not None else None,
        }
        for h in rows
    ]
    watch_keys = await user_data.list_watchlist(session, user_id)
    prefs = await user_data.get_prefs(session, user_id)
    last_seen = prefs.last_seen_at if prefs else None
    return holdings, watch_keys, last_seen


@router.post("", response_model=ChatResponse, dependencies=[Depends(_chat_limit)])
async def chat(
    req: ChatRequest,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """İstifadəçi sualına maliyyə cavabı (grounded debate)."""
    holdings, watch_keys, last_seen = await _load_personal(db, user.id)
    result = await answer(
        req.message, req.lang, db,
        history=[t.model_dump() for t in req.history],
        holdings=holdings, watch_keys=watch_keys, last_seen=last_seen,
    )
    return ChatResponse(**result)


@router.post("/stream", dependencies=[Depends(_chat_limit)])
async def chat_stream(
    req: ChatRequest, user: User = Depends(require_user)
) -> StreamingResponse:
    """Axın cavabı (NDJSON) — qrafik/çip/kart + token-token yazılma effekti.

    Generator öz DB sessiyasını açır (StreamingResponse müddətincə açıq qalsın).
    """
    history = [t.model_dump() for t in req.history]

    async def gen():
        async with AsyncSessionLocal() as session:
            holdings, watch_keys, last_seen = await _load_personal(session, user.id)
            async for event in answer_stream(
                req.message, req.lang, session,
                history=history, holdings=holdings,
                watch_keys=watch_keys, last_seen=last_seen,
            ):
                yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(
        gen(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
