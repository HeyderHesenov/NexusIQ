"""Refresh sessiyası — opaque, DB-saxlanan, SHA-256 hash-lənmiş refresh token.

Refresh JWT DEYİL: reuse detection onsuz da DB oxuması tələb edir, ona görə JWT orada
yalnız alg-confusion səthi əlavə edərdi və revokasiya işləməzdi. `id` = JWT-nin `sid`-i.
Refresh token 256-bit CSPRNG → SHA-256 (Argon2 YOX; brute-force ediləcək insan sirri yoxdur).
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AuthSession(Base, TimestampMixin):
    __tablename__ = "auth_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True
    )
    # Grace window (§2.4): iki-tab benign race üçün əvvəlki hash qısa müddət qəbul olunur.
    previous_token_hash: Mapped[str | None] = mapped_column(String(64))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(  # absolute
        DateTime(timezone=True), nullable=False
    )
    last_used_at: Mapped[datetime] = mapped_column(  # idle
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # logout | logout_all | reuse | password_change | reset | admin
    revoked_reason: Mapped[str | None] = mapped_column(String(24))
    user_agent: Mapped[str | None] = mapped_column(String(200))
    ip: Mapped[str | None] = mapped_column(String(45))

    __table_args__ = (
        Index("ix_auth_sessions_user_revoked", "user_id", "revoked_at"),
        Index("ix_auth_sessions_expires", "expires_at"),
        # Partial indeks: yalnız grace-window sətirlərini indeksləyir (reuse lookup).
        Index(
            "ix_auth_sessions_prev_hash",
            "previous_token_hash",
            postgresql_where=text("previous_token_hash IS NOT NULL"),
        ),
    )

    def __repr__(self) -> str:
        return f"<AuthSession {self.id} user={self.user_id}>"
