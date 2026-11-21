"""Outbound WhatsApp delivery through the Meta Cloud API.

Failures are recorded by the notification service and never raised to callers.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.errors import safe_exception_summary

_TIMEOUT_SECONDS = 10.0
_MAX_BODY_CHARS = 4000


@dataclass(frozen=True)
class DeliveryResult:
    ok: bool
    provider_id: str | None = None
    error: str | None = None
    attempts: int = 0


def is_configured() -> bool:
    return bool(
        settings.WHATSAPP_ENABLED
        and (settings.WHATSAPP_ACCESS_TOKEN or "").strip()
        and (settings.WHATSAPP_PHONE_NUMBER_ID or "").strip()
    )


def send_whatsapp(*, to_phone: str, body: str) -> DeliveryResult:
    """Send one text message. Returns an outcome instead of raising on errors."""
    if not is_configured():
        return DeliveryResult(ok=False, error="WhatsApp transport is not configured")

    url = (
        f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": body[:_MAX_BODY_CHARS]},
    }
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json() if hasattr(response, "json") else {}
        messages = data.get("messages") or []
        provider_id = str(messages[0].get("id")) if messages and messages[0].get("id") else None
        return DeliveryResult(ok=True, provider_id=provider_id, attempts=1)
    except Exception as exc:  # provider/network failures are non-fatal
        return DeliveryResult(
            ok=False,
            error=safe_exception_summary(exc, "WhatsApp delivery"),
            attempts=1,
        )
