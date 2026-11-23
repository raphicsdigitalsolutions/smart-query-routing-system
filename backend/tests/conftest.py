"""Isolated fixtures for Phase 4 tests.

All API tests use a fresh in-memory SQLite database with real SQLAlchemy
operations (no mocked repositories and no access to the development DB).
"""

import os
from collections.abc import Iterator

# Set before importing the app so settings are deterministic in tests.
os.environ["DEBUG"] = "false"
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("JWT_SECRET_KEY", "phase4-test-only-secret-not-for-production")
# The test process can be suspended for hours (laptop sleep, CI queue) between
# minting a token and using it. Production keeps the 60-minute default
# (asserted in tests/test_token_expiry.py); the test environment opts into a
# longer lifetime so wall-clock suspension cannot expire a freshly issued token.
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
# Deterministic non-production encryption key for BYOK unit/integration tests.
os.environ.setdefault(
    "BYOK_ENCRYPTION_KEY",
    "bY9yL1pQ8sN4vR7wX2kT6hE0aF3dJ5cM9uZ8bK1nQ4s=",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.dependencies import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Department, User  # noqa: E402

TEST_PASSWORD = "TestPassword123!"


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(db_engine) -> Iterator[Session]:
    factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    with factory() as session:
        yield session


@pytest.fixture()
def client(db_session) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def departments(db_session) -> dict[str, Department]:
    rows = {
        "registry": Department(name="Registry", description="Student records"),
        "scholarships": Department(name="Scholarships", description="Awards"),
        "other": Department(name="IT Services", description="Technology support"),
    }
    db_session.add_all(rows.values())
    db_session.commit()
    return rows


@pytest.fixture()
def users(db_session, departments) -> dict[str, User]:
    rows = {
        "student": User(
            full_name="Ada Student",
            email="ada@university.edu",
            password_hash=hash_password(TEST_PASSWORD),
            role="student",
        ),
        "student2": User(
            full_name="Ben Student",
            email="ben@university.edu",
            password_hash=hash_password(TEST_PASSWORD),
            role="student",
        ),
        "staff": User(
            full_name="Grace Staff",
            email="grace@university.edu",
            password_hash=hash_password(TEST_PASSWORD),
            role="staff",
            department_id=departments["registry"].id,
        ),
        "staff2": User(
            full_name="Alan Staff",
            email="alan@university.edu",
            password_hash=hash_password(TEST_PASSWORD),
            role="staff",
            department_id=departments["registry"].id,
        ),
        "hod": User(
            full_name="Hilda Hod",
            email="hilda@university.edu",
            password_hash=hash_password(TEST_PASSWORD),
            role="hod",
            department_id=departments["registry"].id,
        ),
        "hod_other": User(
            full_name="Hugo Hod",
            email="hugo@university.edu",
            password_hash=hash_password(TEST_PASSWORD),
            role="hod",
            department_id=departments["other"].id,
        ),
        "admin": User(
            full_name="Alice Admin",
            email="alice@university.edu",
            password_hash=hash_password(TEST_PASSWORD),
            role="admin",
        ),
    }
    db_session.add_all(rows.values())
    db_session.commit()
    return rows


def auth_header(client: TestClient, email: str, password: str = TEST_PASSWORD) -> dict[str, str]:
    """Log in through the real API and return a bearer header."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
