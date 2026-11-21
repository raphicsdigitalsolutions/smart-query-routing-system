"""Create the first administrator account for local development only.

Run from ``backend/`` with::

    python -m app.cli.provision_admin --email admin@university.edu

The password is read from ``ADMIN_PASSWORD`` or, if unset, from a hidden
interactive prompt. No default credentials are stored anywhere. Production
mode exits with an error before touching the database.
"""

import argparse
import getpass
import os
import re
import sys

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app import models  # noqa: F401 - register metadata
from app.core.config import settings
from app.core.enums import UserRole
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Department, User

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Provision the first local admin account")
    parser.add_argument("--email", help="Admin email (or set ADMIN_EMAIL)")
    parser.add_argument(
        "--department-id",
        type=int,
        default=None,
        help="Optional existing department id for the admin",
    )
    return parser.parse_args(argv)


def _resolve_email(argument: str | None) -> str:
    email = (argument or os.getenv("ADMIN_EMAIL") or input("Admin email: ")).strip().lower()
    if not EMAIL_PATTERN.match(email):
        raise ValueError("A valid admin email is required")
    return email


def _resolve_password() -> str:
    password = os.getenv("ADMIN_PASSWORD")
    if password is None:
        password = getpass.getpass("Admin password (input hidden): ")
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        raise ValueError(f"Admin password must be at least {settings.MIN_PASSWORD_LENGTH} characters")
    return password


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if settings.ENVIRONMENT.lower() == "production":
        print("ERROR: admin provisioning is disabled in production mode.", file=sys.stderr)
        return 2

    try:
        email = _resolve_email(args.email)
        password = _resolve_password()
    except (ValueError, EOFError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.role == UserRole.ADMIN.value)) is not None:
            print("ERROR: an admin account already exists; refusing to create another.", file=sys.stderr)
            return 3
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            print("ERROR: that email is already registered.", file=sys.stderr)
            return 4
        if args.department_id is not None and db.get(Department, args.department_id) is None:
            print("ERROR: the supplied department id does not exist.", file=sys.stderr)
            return 5

        admin = User(
            full_name="Local Administrator",
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN.value,
            department_id=args.department_id,
            is_active=True,
        )
        db.add(admin)
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            print("ERROR: could not create the admin account.", file=sys.stderr)
            return 6

    print(f"Admin account created for {email} (id={admin.id}).")
    print("Sign in with POST /api/v1/auth/login. The password was not echoed or stored in plaintext.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
