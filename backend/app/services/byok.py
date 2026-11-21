"""Per-user OpenAI BYOK secret lifecycle.

Every lookup is scoped to the authenticated user's id. No function in this
module returns a plaintext secret except ``resolve_api_key`` (used internally by
the agent); status endpoints receive metadata only. Provider errors are reduced
to a boolean so no key material or provider message can leak to callers.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.encryption import decrypt_secret, encrypt_secret, make_key_hint
from app.core.errors import AppError
from app.models import UserApiKey
from app.schemas.byok import ApiKeyStatusResponse

PROVIDER = "openai"
_VALIDATION_TIMEOUT_SECONDS = 5.0
_MIN_KEY_LENGTH = 8
# Keep the Fernet ciphertext below the 512-character database column. OpenAI
# keys are far shorter; 256 characters still allows future provider formats.
_MAX_KEY_LENGTH = 256

Validator = Callable[[str], bool]


def validate_with_openai(api_key: str) -> bool:
    """Probe OpenAI with ``models.list()`` using the supplied key only.

    Returns a boolean: provider exception text (which may contain credential
    material) is deliberately discarded.
    """
    if not isinstance(api_key, str) or not api_key.strip():
        return False
    try:
        client = OpenAI(
            api_key=api_key,
            timeout=_VALIDATION_TIMEOUT_SECONDS,
            max_retries=0,
        )
        client.models.list()
        return True
    except Exception:
        return False


def default_validator(api_key: str) -> bool:
    """Indirection point so tests can replace the provider validator."""
    return validate_with_openai(api_key)


def _clean_input(api_key: Any) -> str:
    if not isinstance(api_key, str):
        raise AppError("A valid OpenAI API key is required", 400, code="invalid_api_key")
    cleaned = api_key.strip()
    if not (_MIN_KEY_LENGTH <= len(cleaned) <= _MAX_KEY_LENGTH):
        raise AppError("A valid OpenAI API key is required", 400, code="invalid_api_key")
    return cleaned


def _row_for_user(db: Session, user_id: int) -> UserApiKey | None:
    return db.scalar(
        select(UserApiKey).where(
            UserApiKey.user_id == user_id,
            UserApiKey.provider == PROVIDER,
        )
    )


def _status(row: UserApiKey | None) -> ApiKeyStatusResponse:
    if row is None:
        return ApiKeyStatusResponse(
            configured=False,
            has_key=False,
            has_api_key=False,
            is_valid=False,
            status="not_configured",
            key_hint=None,
            validated_at=None,
            last_used_at=None,
        )
    if row.is_valid:
        status = "valid"
    elif row.validated_at is not None:
        status = "invalid"
    else:
        status = "unvalidated"
    return ApiKeyStatusResponse(
        configured=True,
        has_key=True,
        has_api_key=True,
        is_valid=bool(row.is_valid),
        status=status,
        key_hint=row.key_hint,
        validated_at=row.validated_at,
        last_used_at=row.last_used_at,
    )


def _check(validator: Validator, api_key: str) -> bool:
    try:
        return bool(validator(api_key))
    except Exception:
        # Provider messages are never surfaced.
        return False


def get_api_key_status(db: Session, user_id: int) -> ApiKeyStatusResponse:
    """Return non-secret configuration status for one user's key."""
    return _status(_row_for_user(db, user_id))


def save_api_key(
    db: Session,
    user_id: int,
    api_key: str,
    *,
    validator: Validator | None = None,
) -> ApiKeyStatusResponse:
    """Validate then encrypt-and-store (or replace) the user's personal key."""
    cleaned = _clean_input(api_key)
    if not _check(validator or default_validator, cleaned):
        raise AppError("The OpenAI API key was rejected by the provider", 400, code="invalid_api_key")

    encrypted = encrypt_secret(cleaned)
    hint = make_key_hint(cleaned)
    now = datetime.now(timezone.utc)
    row = _row_for_user(db, user_id)
    if row is None:
        row = UserApiKey(
            user_id=user_id,
            provider=PROVIDER,
            encrypted_key=encrypted,
            key_hint=hint,
            is_valid=True,
            validated_at=now,
            last_used_at=None,
        )
        db.add(row)
    else:
        row.encrypted_key = encrypted
        row.key_hint = hint
        row.is_valid = True
        row.validated_at = now
        row.last_used_at = None
    db.commit()
    db.refresh(row)
    return _status(row)


def validate_api_key(
    db: Session,
    user_id: int,
    *,
    api_key: str | None = None,
    validator: Validator | None = None,
) -> ApiKeyStatusResponse:
    """Validate a stored key, or a supplied candidate, for this user only.

    A supplied candidate is never persisted; call save_api_key for that.
    """
    row = _row_for_user(db, user_id)
    if api_key is None:
        if row is None:
            raise AppError("No OpenAI API key is configured", 404, code="api_key_not_found")
        candidate = decrypt_secret(row.encrypted_key)
    else:
        candidate = _clean_input(api_key)

    is_valid = _check(validator or default_validator, candidate)
    # Only a stored-key validation may mutate stored validity metadata.
    if api_key is None and row is not None:
        if is_valid:
            row.is_valid = True
            row.validated_at = datetime.now(timezone.utc)
        else:
            row.is_valid = False
        db.commit()
        db.refresh(row)
    if not is_valid:
        raise AppError("The OpenAI API key was rejected by the provider", 400, code="invalid_api_key")
    return _status(row)


def delete_api_key(db: Session, user_id: int) -> ApiKeyStatusResponse:
    """Delete only the authenticated user's stored key."""
    row = _row_for_user(db, user_id)
    if row is None:
        raise AppError("No OpenAI API key is configured", 404, code="api_key_not_found")
    db.delete(row)
    db.commit()
    return _status(None)


def resolve_api_key(db: Session, user_id: int) -> str | None:
    """Return the user's decrypted key for an agent run, or None if absent.

    This is the only intentional plaintext egress and is never logged.
    """
    row = _row_for_user(db, user_id)
    if row is None:
        return None
    plaintext = decrypt_secret(row.encrypted_key)
    row.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return plaintext


# Descriptive aliases keep the service easy to discover from call sites/tests.
get_status = get_api_key_status
set_api_key = save_api_key
replace_api_key = save_api_key
validate_stored_api_key = validate_api_key
delete_user_api_key = delete_api_key
resolve_user_api_key = resolve_api_key
get_decrypted_api_key = resolve_api_key
