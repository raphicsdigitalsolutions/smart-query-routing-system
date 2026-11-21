"""Authentication, token and role-escalation tests."""

from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models import User
from tests.conftest import TEST_PASSWORD, auth_header

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"


def test_register_creates_student_with_hashed_password(client, db_session) -> None:
    response = client.post(
        REGISTER_URL,
        json={
            "full_name": "New Student",
            "email": "New.Student@University.edu",
            "password": TEST_PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "new.student@university.edu"
    assert body["role"] == "student"
    assert "password" not in body and "password_hash" not in body

    stored = db_session.scalar(select(User).where(User.email == "new.student@university.edu"))
    assert stored is not None
    assert stored.password_hash.startswith("$argon2")
    assert stored.password_hash != TEST_PASSWORD
    assert verify_password(TEST_PASSWORD, stored.password_hash)


def test_duplicate_email_registration_is_rejected(client, users) -> None:
    response = client.post(
        REGISTER_URL,
        json={"full_name": "Impostor", "email": users["student"].email, "password": TEST_PASSWORD},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "duplicate_email"


def test_public_registration_cannot_escalate_role_or_set_department(client, departments) -> None:
    response = client.post(
        REGISTER_URL,
        json={
            "full_name": "Sneaky User",
            "email": "sneaky@university.edu",
            "password": TEST_PASSWORD,
            "role": "admin",
            "department_id": departments["registry"].id,
            "is_active": False,
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "student"
    assert response.json()["department_id"] is None
    assert response.json()["is_active"] is True


def test_password_hash_helper_rejects_wrong_password() -> None:
    hashed = hash_password(TEST_PASSWORD)
    assert hashed != TEST_PASSWORD
    assert verify_password(TEST_PASSWORD, hashed) is True
    assert verify_password("wrong-password", hashed) is False
    assert verify_password(TEST_PASSWORD, "!") is False


def test_login_success_returns_token_and_safe_user_payload(client, users) -> None:
    response = client.post(
        LOGIN_URL, json={"email": users["student"].email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert body["user"]["role"] == "student"
    assert "password" not in body["user"] and "password_hash" not in body["user"]


def test_login_invalid_credentials_are_generic(client, users) -> None:
    for email, password in [
        (users["student"].email, "wrong-password"),
        ("nobody@university.edu", TEST_PASSWORD),
    ]:
        response = client.post(LOGIN_URL, json={"email": email, "password": password})
        assert response.status_code == 401
        assert response.json() == {
            "success": False,
            "error": "Invalid email or password",
            "detail": None,
            "code": "invalid_credentials",
        }


def test_me_requires_a_valid_token(client, users) -> None:
    assert client.get(ME_URL).status_code == 401

    headers = auth_header(client, users["student"].email)
    response = client.get(ME_URL, headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == users["student"].email
    assert "password_hash" not in response.json()


def test_invalid_and_expired_tokens_are_rejected(client) -> None:
    invalid = client.get(ME_URL, headers={"Authorization": "Bearer not-a-jwt"})
    assert invalid.status_code == 401
    assert invalid.json()["code"] == "invalid_token"

    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {
            "sub": "1",
            "role": "student",
            "type": "access",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    response = client.get(ME_URL, headers={"Authorization": f"Bearer {expired}"})
    assert response.status_code == 401
    assert response.json()["code"] == "token_expired"


def test_inactive_account_cannot_authenticate(client, db_session, users) -> None:
    users["staff"].is_active = False
    db_session.commit()

    assert client.post(
        LOGIN_URL, json={"email": users["staff"].email, "password": TEST_PASSWORD}
    ).status_code == 401
