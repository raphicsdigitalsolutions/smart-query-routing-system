"""Deterministic access-token expiry regression tests (Task 1).

The full suite once failed with ``401 token_expired`` because the host was
suspended for ~17 hours between minting and using a token while the token
lifetime was 60 minutes. Production must keep the short lifetime, so the test
environment uses a long lifetime and these tests pin both behaviors.
"""

from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import Settings, settings
from app.core.security import create_access_token, decode_access_token
from app.models import User
from tests.conftest import auth_header

ME_URL = "/api/v1/auth/me"


def test_production_default_token_lifetime_is_unchanged() -> None:
    field = Settings.model_fields["ACCESS_TOKEN_EXPIRE_MINUTES"]
    assert field.default == 60, "Production token lifetime default must stay 60 minutes"


def test_test_environment_uses_long_lifetime_for_wall_clock_suspension() -> None:
    assert settings.ENVIRONMENT == "testing"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES >= 12 * 60


def test_issued_token_expiry_uses_configured_lifetime_exactly() -> None:
    token, expires_in = create_access_token(123, "student")
    payload = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})

    assert expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    lifetime = payload["exp"] - payload["iat"]
    assert lifetime == expires_in
    # Tests must never mint tokens that outlive a day by accident.
    assert lifetime <= 7 * 24 * 60 * 60


def test_expiry_boundary_is_enforced_without_extending_lifetime(client, users) -> None:
    now = datetime.now(timezone.utc)

    def encode(exp: datetime) -> str:
        return jwt.encode(
            {
                "sub": str(users["student"].id),
                "role": "student",
                "type": "access",
                "iat": now - timedelta(minutes=5),
                "exp": exp,
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    expired = client.get(ME_URL, headers={"Authorization": f"Bearer {encode(now - timedelta(seconds=5))}"})
    assert expired.status_code == 401
    assert expired.json()["code"] == "token_expired"

    # A fresh login token is valid and belongs to the right user.
    fresh = auth_header(client, users["student"].email)
    me = client.get(ME_URL, headers=fresh)
    assert me.status_code == 200
    assert me.json()["email"] == users["student"].email


def test_decode_access_token_rejects_expired_payload_without_clock_dependency() -> None:
    """Direct deterministic check: expired payload rejected, valid payload accepted."""
    now = datetime.now(timezone.utc)

    def encode(exp: datetime) -> str:
        return jwt.encode(
            {
                "sub": "1",
                "role": "student",
                "type": "access",
                "iat": now - timedelta(minutes=10),
                "exp": exp,
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

    assert decode_access_token(encode(now + timedelta(minutes=1)))["sub"] == "1"

    from app.core.errors import AppError

    try:
        decode_access_token(encode(now - timedelta(seconds=1)))
    except AppError as exc:
        assert exc.status_code == 401
        assert exc.code == "token_expired"
    else:  # pragma: no cover - explicit failure path
        raise AssertionError("Expired token was accepted")
