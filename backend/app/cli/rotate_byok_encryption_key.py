"""Safely rotate the Fernet key used for encrypted per-user BYOK secrets.

Keys are read only from environment variables so they never appear in shell
history or process arguments:

    BYOK_ROTATION_OLD_KEY=<current key> \
    BYOK_ROTATION_NEW_KEY=<new key> \
    python -m app.cli.rotate_byok_encryption_key --dry-run

    BYOK_ROTATION_OLD_KEY=<current key> \
    BYOK_ROTATION_NEW_KEY=<new key> \
    python -m app.cli.rotate_byok_encryption_key --commit

The dry-run decrypts every stored key with the old key but changes nothing.
The commit path decrypts all rows first, re-encrypts them in one transaction,
verifies every row with the new key, and only then commits. No plaintext secret
or key value is ever printed.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import UserApiKey

_OLD_KEY_ENV = "BYOK_ROTATION_OLD_KEY"
_NEW_KEY_ENV = "BYOK_ROTATION_NEW_KEY"


def _fernet(value: str, env_name: str) -> Fernet:
    if not value or not value.strip():
        raise ValueError(f"{env_name} is required")
    try:
        return Fernet(value.strip().encode("utf-8"))
    except (TypeError, ValueError):
        raise ValueError(f"{env_name} must be a valid Fernet key") from None


def rotate_user_api_key_encryption(
    db: Session,
    old_key: str,
    new_key: str,
    *,
    commit: bool = False,
) -> dict[str, Any]:
    """Decrypt all rows with ``old_key`` and optionally re-encrypt with ``new_key``.

    Returns counts only. Raises before any write if any row cannot be decrypted
    with the old key, and rolls back if verification with the new key fails.
    """
    old = _fernet(old_key, _OLD_KEY_ENV)
    new = _fernet(new_key, _NEW_KEY_ENV)
    if old_key.strip() == new_key.strip():
        raise ValueError("The old and new Fernet keys must be different")

    rows = list(db.scalars(select(UserApiKey)).all())
    prepared: list[tuple[UserApiKey, str]] = []
    for row in rows:
        try:
            plaintext = old.decrypt(str(row.encrypted_key).encode("ascii")).decode("utf-8")
        except (InvalidToken, UnicodeError, TypeError, ValueError):
            raise RuntimeError(
                f"BYOK row id {row.id} cannot be decrypted with the old key; rotation aborted"
            ) from None
        prepared.append((row, plaintext))

    if not commit:
        return {"rows": len(prepared), "changed": 0, "committed": False}

    try:
        for row, plaintext in prepared:
            row.encrypted_key = new.encrypt(plaintext.encode("utf-8")).decode("ascii")
        db.flush()
        for row, plaintext in prepared:
            verified = new.decrypt(str(row.encrypted_key).encode("ascii")).decode("utf-8")
            if verified != plaintext:
                raise RuntimeError("BYOK rotation verification failed; changes were rolled back")
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"rows": len(prepared), "changed": len(prepared), "committed": True}


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rotate encrypted BYOK storage keys safely")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Decrypt every row with the old key without writing (default).",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Actually re-encrypt rows and commit. Requires explicit opt-in.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.commit and args.dry_run:
        print("ERROR: choose either --dry-run or --commit, not both.", file=sys.stderr)
        return 2

    old_key = os.getenv(_OLD_KEY_ENV, "")
    new_key = os.getenv(_NEW_KEY_ENV, "")
    commit = args.commit

    try:
        with SessionLocal() as db:
            result = rotate_user_api_key_encryption(db, old_key, new_key, commit=commit)
    except (ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    mode = "commit" if commit else "dry-run"
    print(
        "mode={mode} rows={rows} changed={changed} committed={committed}".format(
            mode=mode,
            rows=result["rows"],
            changed=result["changed"],
            committed=str(result["committed"]).lower(),
        )
    )
    if commit:
        print(
            "Rotation committed. Update BYOK_ENCRYPTION_KEY in the secret manager, "
            "restart the application, and verify BYOK status. No keys were printed."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
