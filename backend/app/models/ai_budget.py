"""AI xərc uçotu (ai_usage) + sistem bayraqları (system_flags — kill switch).

Request səviyyəsində ölçülür (token yox): çağırışdan ƏVVƏL qərar verməlisən, token
xərcini yalnız SONRA öyrənirsən. `user_id NULL` = planlayıcı/sistem (qlobal cap-a sayılır,
yoxsa qlobal cap yalandır). Kill switch env-də YOX, DB-də — deploy tələb edən kill switch
kill switch deyil.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AiUsage(Base):
    __tablename__ = "ai_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # NULL = planlayıcı/sistem. User silinsə uçot tarixi qalsın (qlobal aqreqat) → SET NULL.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    route: Mapped[str] = mapped_column(String(48), nullable=False)
    # weight — chat ~4 LLM çağırışıdır, radar explain 1-dir; bərabər tutmaq səhvdir.
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_ai_usage_user_created", "user_id", "created_at"),
        Index("ix_ai_usage_created", "created_at"),
    )


class SystemFlag(Base, TimestampMixin):
    __tablename__ = "system_flags"

    key: Mapped[str] = mapped_column(String(48), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(64))
