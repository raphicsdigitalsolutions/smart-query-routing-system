"""Deterministic redaction applied before ticket text enters a prompt.

Agents receive only the ticket subject and description, never the student's
name, email, password hash, internal notes or other domain records. This module
additionally removes obvious identifiers and credential-like strings that a
student may accidentally paste into the ticket body.
"""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"\b(password|passwd|pwd|token|api[_-]?key|secret|otp|pin)\s*[:=]\s*\S+",
    re.IGNORECASE,
)
_PROVIDER_TOKEN_RE = re.compile(r"\b(?:sk|pk|rk)[-_][A-Za-z0-9_-]{12,}\b", re.IGNORECASE)
_LONG_DIGITS_RE = re.compile(r"\b\d{8,}\b")


def sanitize_ticket_text(value: str, *, max_chars: int = 10_000) -> str:
    """Remove obvious secrets/contact details and cap untrusted prompt text."""
    text = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = _PROVIDER_TOKEN_RE.sub("[REDACTED_TOKEN]", text)
    text = _SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", text)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = _PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = _LONG_DIGITS_RE.sub("[REDACTED_NUMBER]", text)
    if len(text) > max_chars:
        text = f"{text[:max_chars]}\n[truncated for safety]"
    return text.strip()
