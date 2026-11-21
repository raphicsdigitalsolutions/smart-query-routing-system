"""Fernet-backed encryption for user-supplied provider secrets.

The encryption key comes exclusively from server configuration. Plaintext keys,
ciphertext and display hints are never logged or included in error messages.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.errors import AppError

_SECRET_STORE_ERROR = "Secure secret storage is not configured on the server."
_HINT_PREFIX = "****"


def _fernet() -> Fernet:
    """Build a Fernet instance, failing closed when configuration is unusable."""
    key = (settings.BYOK_ENCRYPTION_KEY or "").strip()
    if not key:
        raise AppError(_SECRET_STORE_ERROR, 503, code="secret_store_not_configured")
    try:
        return Fernet(key.encode("utf-8"))
    except (TypeError, ValueError):
        # Never include the configured value in the error or in logs.
        raise AppError(_SECRET_STORE_ERROR, 503, code="secret_store_not_configured") from None


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret; returns an ASCII Fernet token."""
    fernet = _fernet()
    if not isinstance(plaintext, str) or not plaintext:
        raise AppError("A non-empty secret is required", 400, code="invalid_api_key")
    try:
        return fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")
    except (TypeError, ValueError, UnicodeError):
        raise AppError("The secret could not be encrypted", 503, code="secret_store_not_configured") from None


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a stored secret, failing closed on unusable configuration/data."""
    fernet = _fernet()
    if not isinstance(ciphertext, str) or not ciphertext:
        raise AppError("Stored credentials are unavailable", 503, code="secret_store_not_configured")
    try:
        return fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError, TypeError, ValueError):
        raise AppError("Stored credentials could not be read", 503, code="secret_store_not_configured") from None


def make_key_hint(plaintext: str) -> str:
    """Return a display-only hint built from the last four characters.

    The full key is never returned, logged or derivable from this value.
    """
    if not isinstance(plaintext, str) or len(plaintext.strip()) < 4:
        return _HINT_PREFIX
    return f"{_HINT_PREFIX}{plaintext.strip()[-4:]}"
