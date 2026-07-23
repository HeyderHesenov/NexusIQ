"""Auth audit log — təhlükəsizlik hadisələrinin yazılması / oxunması / təmizliyi.

`record_audit` ÖZ session-u açır (request `db`-si YOX). Səbəb: `login_failure`/
`reuse_detected` kimi hadisələr auth_service-in ARTIQ commit etdiyi (kilid sayğacı)
yollarda baş verir; audit yazısını request tranzaksiyasına bağlamaq həm əlavə commit,
həm də səhv-yol vəziyyətindən asılılıq deməkdir. Ayrı, fire-and-forget commit → hadisə
həmişə qalır. Bu, `budget.record_system_usage`-in eyni nümunəsidir.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Request
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clientip import client_ip
from app.models.audit_log import AuthAuditLog


async def record_audit(
    user_id: uuid.UUID | None,
    event: str,
    request: Request,
    *,
    meta: dict | None = None,
) -> None:
    """Bir təhlükəsizlik hadisəsini yaz (öz session, ayrı commit)."""
    from app.db.session import AsyncSessionLocal

    ua = request.headers.get("user-agent")
    async with AsyncSessionLocal() as s:
        s.add(
            AuthAuditLog(
                user_id=user_id,
                event=event[:32],
                ip=client_ip(request),
                user_agent=ua[:200] if ua else None,
                meta=meta,
            )
        )
        await s.commit()


async def list_recent(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int = 50
) -> list[AuthAuditLog]:
    """İstifadəçinin öz son hadisələri — ən yenisi əvvəl."""
    rows = await session.scalars(
        select(AuthAuditLog)
        .where(AuthAuditLog.user_id == user_id)
        .order_by(AuthAuditLog.created_at.desc())
        .limit(limit)
    )
    return list(rows)


async def cleanup_audit(session: AsyncSession, *, keep_days: int = 90) -> int:
    """keep_days-dən köhnə audit sətirlərini sil (retention job)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    result = await session.execute(
        delete(AuthAuditLog).where(AuthAuditLog.created_at < cutoff)
    )
    await session.commit()
    return result.rowcount or 0
