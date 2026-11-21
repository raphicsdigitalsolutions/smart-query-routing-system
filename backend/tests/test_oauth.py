"""Google OAuth2: disabled gating, mocked sign-in and offline token verification."""

import base64
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import select

from app.api.routes.oauth import router as oauth_router
from app.core.config import settings
from app.core.errors import AppError
from app.main import app
from app.models import AuditLog, User, UserOauthAccount
from app.services import oauth_google

BASE = "/api/v1/auth/google"

if not any(getattr(route, "path", None) == f"{settings.API_V1_PREFIX}/auth/google" for route in app.routes):
    app.include_router(oauth_router, prefix=settings.API_V1_PREFIX)


def claims(**overrides):
    payload = {
        "sub": "google-subject-123",
        "email": "new.google@university.edu",
        "email_verified": True,
        "name": "New Google User",
        "iss": "https://accounts.google.com",
        "aud": "test-client-id",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        "iat": datetime.now(timezone.utc),
    }
    payload.update(overrides)
    return payload


def enable(monkeypatch, client_id: str = "test-client-id") -> None:
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_ENABLED", True)
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", client_id)


def test_google_login_denied_when_disabled(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_ENABLED", False)
    response = client.post(BASE, json={"credential": "anything"})
    assert response.status_code == 503, response.text
    assert response.json()["code"] == "oauth_not_configured"
    assert response.json()["success"] is False


def test_google_login_creates_student_links_account_and_audits(client, db_session, monkeypatch) -> None:
    enable(monkeypatch)
    monkeypatch.setattr(oauth_google, "verify_google_id_token", lambda credential: claims())

    response = client.post(BASE, json={"credential": "signed-token"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert body["user"]["role"] == "student"
    assert body["user"]["email"] == "new.google@university.edu"
    assert "password" not in body and "password_hash" not in body

    user = db_session.scalar(select(User).where(User.email == "new.google@university.edu"))
    assert user is not None and user.role == "student"
    assert user.password_hash.startswith("$argon2")
    link = db_session.scalar(select(UserOauthAccount).where(UserOauthAccount.user_id == user.id))
    assert link.provider == "google"
    assert link.provider_subject == "google-subject-123"
    assert link.linked_at is not None

    audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "auth.google_login"))
    assert audit is not None
    assert audit.actor_id == user.id
    assert audit.entity_type == "user"

    # The returned token works against the standard authenticated endpoint.
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["id"] == user.id


def test_google_login_reuses_existing_user_and_never_creates_admin(client, db_session, monkeypatch, users) -> None:
    enable(monkeypatch)
    monkeypatch.setattr(
        oauth_google,
        "verify_google_id_token",
        lambda credential: claims(
            sub="google-subject-456",
            email=users["student"].email,
            role="admin",  # a token must never provision a privileged account
        ),
    )
    response = client.post(BASE, json={"credential": "signed-token"})
    assert response.status_code == 200, response.text
    assert response.json()["user"]["id"] == users["student"].id
    assert response.json()["user"]["role"] == "student"

    emails = db_session.scalars(select(User.email)).all()
    assert emails.count(users["student"].email) == 1
    link = db_session.scalar(
        select(UserOauthAccount).where(UserOauthAccount.provider_subject == "google-subject-456")
    )
    assert link.user_id == users["student"].id


def test_google_login_rejects_bad_credential(client, monkeypatch) -> None:
    enable(monkeypatch)

    def reject(_: str):
        raise AppError("Invalid Google ID token", 401, code="invalid_google_token")

    monkeypatch.setattr(oauth_google, "verify_google_id_token", reject)
    response = client.post(BASE, json={"credential": "bad"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_google_token"


# ---------------------------------------------------------------------------
# Offline verification with a locally generated RSA key (no network, no Google).
# ---------------------------------------------------------------------------
def _b64url_int(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


@pytest.fixture()
def local_jwks(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": "local-test-key",
        "use": "sig",
        "alg": "RS256",
        "n": _b64url_int(numbers.n),
        "e": _b64url_int(numbers.e),
    }
    monkeypatch.setattr(oauth_google, "_fetch_google_jwks", lambda: {"keys": [jwk]})
    return private_key


def test_verify_google_id_token_offline(local_jwks, monkeypatch) -> None:
    enable(monkeypatch)
    token = jwt.encode(
        claims(), local_jwks, algorithm="RS256", headers={"kid": "local-test-key"}
    )
    verified = oauth_google.verify_google_id_token(token)
    assert verified["sub"] == "google-subject-123"
    assert verified["email"] == "new.google@university.edu"


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "wrong-client"},
        {"iss": "https://evil.example.com"},
        {"email_verified": False},
        {"exp": datetime.now(timezone.utc) - timedelta(minutes=5)},
    ],
)
def test_verify_google_id_token_rejects_invalid_claims(local_jwks, monkeypatch, overrides) -> None:
    enable(monkeypatch)
    token = jwt.encode(
        claims(**overrides), local_jwks, algorithm="RS256", headers={"kid": "local-test-key"}
    )
    with pytest.raises(AppError) as error:
        oauth_google.verify_google_id_token(token)
    assert error.value.status_code == 401
    assert error.value.code == "invalid_google_token"


def test_verify_google_id_token_rejects_unknown_kid(local_jwks, monkeypatch) -> None:
    enable(monkeypatch)
    token = jwt.encode(
        claims(), local_jwks, algorithm="RS256", headers={"kid": "unknown-key"}
    )
    with pytest.raises(AppError) as error:
        oauth_google.verify_google_id_token(token)
    assert error.value.code == "invalid_google_token"
