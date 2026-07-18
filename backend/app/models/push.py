"""Web Push abunəsi modeli — brauzer bildirişləri üçün."""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class PushSubscription(Base, TimestampMixin):
    """Bir brauzer abunəsi. Endpoint + şifrələmə açarları + sahib.

    Frontend `PushManager.subscribe()` nəticəsi burada saxlanır;
    yeni xəbər yarananda bu endpointlərə bildiriş göndərilir.
    """

    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Sahib — NOT NULL. Nullable sahib "bu sətir kimindir?" budağı = növbəti IDOR.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(String(255), nullable=False)
    auth: Mapped[str] = mapped_column(String(255), nullable=False)
    # İstifadəçinin seçdiyi dil — bildiriş mətni bu dildə gedə bilər.
    lang: Mapped[str] = mapped_column(String(5), default="az", nullable=False)

    __table_args__ = (Index("ix_push_subscriptions_user", "user_id"),)

    def __repr__(self) -> str:
        return f"<PushSubscription {self.endpoint[:40]!r}…>"
