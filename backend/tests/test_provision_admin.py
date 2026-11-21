"""Dev-only admin provisioning safeguards."""

import pytest
from sqlalchemy import select

import app.cli.provision_admin as cli
from app.core.config import settings
from app.core.enums import UserRole
from app.core.security import verify_password
from app.models import User
from tests.conftest import TEST_PASSWORD


@pytest.fixture()
def cli_db(db_session, monkeypatch):
    """Point the CLI at the isolated test session factory."""
    monkeypatch.setattr(cli, "SessionLocal", lambda: db_session)
    return db_session


def test_provisioning_is_rejected_in_production(cli_db, monkeypatch, capsys) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setenv("ADMIN_PASSWORD", TEST_PASSWORD)

    assert cli.main(["--email", "prod@university.edu"]) == 2
    assert "disabled in production" in capsys.readouterr().err
    assert cli_db.scalar(select(User).where(User.email == "prod@university.edu")) is None


def test_first_admin_is_created_with_hashed_password(cli_db, monkeypatch, capsys) -> None:
    monkeypatch.setenv("ADMIN_EMAIL", "first-admin@university.edu")
    monkeypatch.setenv("ADMIN_PASSWORD", TEST_PASSWORD)

    assert cli.main([]) == 0
    out = capsys.readouterr().out
    assert TEST_PASSWORD not in out

    admin = cli_db.scalar(select(User).where(User.email == "first-admin@university.edu"))
    assert admin is not None
    assert admin.role == UserRole.ADMIN.value
    assert admin.password_hash.startswith("$argon2")
    assert verify_password(TEST_PASSWORD, admin.password_hash)


def test_duplicate_admin_is_refused(cli_db, monkeypatch) -> None:
    cli_db.add(
        User(
            full_name="Existing Admin",
            email="existing@university.edu",
            password_hash="hash",
            role=UserRole.ADMIN.value,
        )
    )
    cli_db.commit()
    monkeypatch.setenv("ADMIN_PASSWORD", TEST_PASSWORD)

    assert cli.main(["--email", "second@university.edu"]) == 3
    assert cli_db.scalar(select(User).where(User.email == "second@university.edu")) is None


def test_weak_password_is_rejected(cli_db, monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_PASSWORD", "short")
    assert cli.main(["--email", "weak@university.edu"]) == 2
