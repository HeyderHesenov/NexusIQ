"""Auth audit log (auth_audit_log) — append-only təhlükəsizlik hadisələri.

Login/parol/reset/sessiya-ləğvi hadisələri qeyd olunur. `user_id NULL` = naməlum
email ilə cəhd (login_failure/locked, reuse) və ya user sonradan silinib. Sətirlər
ÖZ session-u ilə yazılır (`services/audit.record_audit`) ki, uğursuz-yol request
tranzaksiyasının rollback-ı audit sətrini atmasın.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuthAuditLog(Base):
    __tablename__ = "auth_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # NULL = naməlum-email cəhdi (login_failure) və ya user silinib → tarix qalsın.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    event: Mapped[str] = mapped_column(String(32), nullable=False)
    ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(200))
    meta: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_auth_audit_user_created", "user_id", "created_at"),
        Index("ix_auth_audit_created", "created_at"),
    )
