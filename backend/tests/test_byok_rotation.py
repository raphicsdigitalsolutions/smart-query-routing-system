"""Regression tests for safe BYOK encryption-key rotation."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.cli.rotate_byok_encryption_key import rotate_user_api_key_encryption
from app.models import UserApiKey

_PLAINTEXT = "value-rotation-one"


def _row(db: Session, user_id: int, ciphertext: str) -> UserApiKey:
    row = UserApiKey(
        user_id=user_id,
        provider="openai",
        encrypted_key=ciphertext,
        key_hint="****one",
        is_valid=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_dry_run_decrypts_without_changing_rows(db_session: Session, users: dict) -> None:
    old_key = Fernet.generate_key().decode("ascii")
    new_key = Fernet.generate_key().decode("ascii")
    ciphertext = Fernet(old_key).encrypt(_PLAINTEXT.encode("utf-8")).decode("ascii")
    row = _row(db_session, users["student"].id, ciphertext)

    result = rotate_user_api_key_encryption(db_session, old_key, new_key, commit=False)

    assert result == {"rows": 1, "changed": 0, "committed": False}
    db_session.refresh(row)
    assert row.encrypted_key == ciphertext
    assert Fernet(old_key).decrypt(row.encrypted_key.encode("ascii")).decode("utf-8") == _PLAINTEXT


def test_commit_rotates_ciphertext_and_preserves_metadata(db_session: Session, users: dict) -> None:
    old_key = Fernet.generate_key().decode("ascii")
    new_key = Fernet.generate_key().decode("ascii")
    ciphertext = Fernet(old_key).encrypt(_PLAINTEXT.encode("utf-8")).decode("ascii")
    row = _row(db_session, users["student"].id, ciphertext)
    original_user_id = row.user_id
    original_provider = row.provider
    original_hint = row.key_hint
    original_valid = row.is_valid
    original_validated_at = row.validated_at

    result = rotate_user_api_key_encryption(db_session, old_key, new_key, commit=True)

    assert result == {"rows": 1, "changed": 1, "committed": True}
    db_session.refresh(row)
    assert row.user_id == original_user_id
    assert row.provider == original_provider
    assert row.key_hint == original_hint
    assert row.is_valid == original_valid
    assert row.validated_at == original_validated_at
    assert Fernet(new_key).decrypt(row.encrypted_key.encode("ascii")).decode("utf-8") == _PLAINTEXT
    with pytest.raises(InvalidToken):
        Fernet(old_key).decrypt(row.encrypted_key.encode("ascii"))


def test_undecryptable_row_aborts_before_any_write(db_session: Session, users: dict) -> None:
    old_key = Fernet.generate_key().decode("ascii")
    new_key = Fernet.generate_key().decode("ascii")
    row = _row(db_session, users["student"].id, "not-a-fernet-token")

    with pytest.raises(RuntimeError, match="cannot be decrypted"):
        rotate_user_api_key_encryption(db_session, old_key, new_key, commit=True)

    db_session.refresh(row)
    assert row.encrypted_key == "not-a-fernet-token"


def test_rotation_rejects_invalid_or_identical_keys(db_session: Session) -> None:
    key = Fernet.generate_key().decode("ascii")
    with pytest.raises(ValueError, match="different"):
        rotate_user_api_key_encryption(db_session, key, key, commit=False)
    with pytest.raises(ValueError, match="valid Fernet"):
        rotate_user_api_key_encryption(db_session, key, "not-a-key", commit=False)


def test_rotation_handles_empty_table(db_session: Session) -> None:
    old_key = Fernet.generate_key().decode("ascii")
    new_key = Fernet.generate_key().decode("ascii")
    result = rotate_user_api_key_encryption(db_session, old_key, new_key, commit=True)
    assert result == {"rows": 0, "changed": 0, "committed": True}
