"""Password hashing and JWT helpers.

The JWT signing key is read from configuration. Production refuses to start
without an explicit ``JWT_SECRET_KEY``; development generates an ephemeral
key per process (tokens therefore stop being valid after a restart).
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)

_hasher = PasswordHasher()
_dev_secret: str | None = None


def get_jwt_secret() -> str:
    """Return the configured secret, or a process-local development fallback."""
    global _dev_secret
    if settings.JWT_SECRET_KEY:
        return settings.JWT_SECRET_KEY
    if settings.ENVIRONMENT.lower() == "production":
        # Failing closed is intentional: never silently use a weak default key.
        raise RuntimeError("JWT_SECRET_KEY must be configured in production")
    if _dev_secret is None:
        _dev_secret = secrets.token_urlsafe(48)
        logger.warning(
            "JWT_SECRET_KEY is unset; using an ephemeral development secret. "
            "Tokens will be invalidated on restart."
        )
    return _dev_secret


def hash_password(password: str) -> str:
    """Return an Argon2id PHC hash. Plaintext is never persisted."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Verify a password without leaking hash details to callers."""
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(subject: int | str, role: str) -> tuple[str, int]:
    """Create a short-lived access token. Returns ``(token, expires_in_seconds)``."""
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, get_jwt_secret(), algorithm=settings.JWT_ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token; raise a safe 401 AppError on failure."""
    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AppError("Access token has expired", 401, code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise AppError("Invalid access token", 401, code="invalid_token") from exc

    if payload.get("type") != "access" or not payload.get("sub"):
        raise AppError("Invalid access token", 401, code="invalid_token")
    return payload
