"""Email göndərmə — Protocol + Console (dev) / SMTP (prod, inert).

Provayder olmadan email doğrulamaq mümkün deyil (hər şey teatrdır). Ona görə tam axın
indi qurulur, amma inert: dev-də link backend loquna yazılır (ConsoleEmailSender),
prod-da SMTP konfiqurasiya olunanda aktivləşir.
"""
from __future__ import annotations

import logging
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger("nexusiq.email")


class EmailSender(Protocol):
    async def send(self, to: str, subject: str, body: str) -> None: ...


class ConsoleEmailSender:
    """Dev — email göndərmir, linki loga yazır."""

    async def send(self, to: str, subject: str, body: str) -> None:
        logger.info("EMAIL[console] to=%s subject=%s\n%s", to, subject, body)


class SmtpEmailSender:
    """Prod — aiosmtplib. SMTP konfiqurasiya olunmayana qədər çağırılmır."""

    async def send(self, to: str, subject: str, body: str) -> None:
        import aiosmtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"] = settings.smtp_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.set_content(body)
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_tls,
            timeout=10,
        )


def get_email_sender() -> EmailSender:
    """SMTP konfiqurasiya olunubsa SMTP, əks halda Console."""
    if settings.smtp_host:
        return SmtpEmailSender()
    return ConsoleEmailSender()
