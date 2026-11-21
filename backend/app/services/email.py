"""SMTP email transport built on the Python standard library.

Delivery is best-effort: transport errors are returned as structured results
and are never raised into ticket operations. Credentials are only used for
SMTP AUTH and are never logged or exposed through an API.
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import settings
from app.core.errors import safe_exception_summary

# Reserved documentation domains are treated as "not configured" so local
# development and the test-suite never attempt a real network connection.
_PLACEHOLDER_SUFFIXES = (".example.com", ".example.net", ".example.org", ".invalid")


@dataclass(frozen=True)
class DeliveryResult:
    ok: bool
    provider_id: str | None = None
    error: str | None = None
    attempts: int = 0


def is_configured() -> bool:
    """True only when an outward email transport can realistically be used."""
    host = (settings.SMTP_HOST or "").strip().lower()
    if not settings.EMAIL_NOTIFICATIONS_ENABLED or not host:
        return False
    return not any(host.endswith(suffix) for suffix in _PLACEHOLDER_SUFFIXES)


def _build_message(to_address: str, subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = settings.MAIL_FROM
    message["To"] = to_address
    message["Subject"] = " ".join(str(subject).split())
    message.set_content(body)
    return message


def send_email(*, to_address: str, subject: str, body: str) -> DeliveryResult:
    """Attempt delivery with bounded retries; return the outcome, never raise."""
    if not is_configured():
        return DeliveryResult(ok=False, error="email transport is not configured")

    message = _build_message(to_address, subject, body)
    attempts = 0
    last_error = "unknown SMTP error"
    for attempt in range(1, max(1, settings.SMTP_ATTEMPTS) + 1):
        attempts = attempt
        try:
            if settings.SMTP_USE_SSL:
                client: smtplib.SMTP = smtplib.SMTP_SSL(
                    settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS
                )
            else:
                client = smtplib.SMTP(
                    settings.SMTP_HOST, settings.SMTP_PORT, timeout=settings.SMTP_TIMEOUT_SECONDS
                )
            with client:
                if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
                    client.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    client.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                client.send_message(message)
            return DeliveryResult(ok=True, attempts=attempts)
        except Exception as exc:  # network/auth errors must not break ticket flows
            last_error = safe_exception_summary(exc, "SMTP delivery")

    return DeliveryResult(ok=False, error=last_error, attempts=attempts)
