"""İstifadəçi + xarici identity (Google) modelləri.

UUID PK (uuid4, Python-da — pgcrypto asılılığı yox). bigserial DEYİL: JWT/loglarda
görünən id istifadəçi sayını sızdırmasın və IDOR-by-increment dəvət etməsin.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # CHECK (email = lower(email)) → skriptdən belə normalizasiyasız sətir DÜŞMÜR.
    # Normalizasiya YALNIZ lowercase — gmail nöqtə/+tag aliasing ETMƏ (merge bug-ları).
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Google-only istifadəçidə NULL (parol yoxdur). Tam PHC string burada saxlanır
    # → Argon2 parametrləri hash ilə səyahət edir (rehash konfiq dəyişikliyidir, migrasiya yox).
    password_hash: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(80))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    # server_default-lar migrasiya ilə eyni saxlanır (alembic check drift verməsin).
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, default="user", server_default="user"
    )
    is_active: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default=text("true")
    )

    # ---- Login backoff (DB-də, limiter-də YOX — restart lockout-u silməsin) ----
    failed_login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # logout-all: bu vaxtdan ƏVVƏL verilmiş access token-lər rədd (require_user yoxlayır).
    sessions_valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("email = lower(email)", name="ck_users_email_lower"),
    )

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email}>"


class UserIdentity(Base):
    """Xarici provayder bağlantısı. Bağlama `sub` üzrə, HEÇ VAXT email üzrə
    (email dəyişkəndir və Workspace-də başqa insana verilə bilər — ATO bug-u)."""

    __tablename__ = "user_identities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(16), nullable=False)  # 'google'
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)  # sub
    email_at_link: Mapped[str | None] = mapped_column(String(254))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_identity_provider_sub"),
        Index("ix_user_identities_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<UserIdentity {self.provider}:{self.provider_subject}>"
