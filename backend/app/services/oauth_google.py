"""Offline-testable Google ID-token verification and account linking."""

import json
import secrets
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import UserRole
from app.core.errors import AppError
from app.core.security import hash_password
from app.models import User, UserOauthAccount

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
GOOGLE_JWKS_TIMEOUT_SECONDS = 10.0


def _invalid_token() -> AppError:
    return AppError("Invalid Google ID token", 401, code="invalid_google_token")


@lru_cache(maxsize=1)
def _fetch_google_jwks() -> dict[str, Any]:
    """Fetch Google's public signing keys (replaced wholesale in tests)."""
    try:
        response = httpx.get(GOOGLE_JWKS_URL, timeout=GOOGLE_JWKS_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise AppError(
            "Google token verification is currently unavailable",
            503,
            code="oauth_verification_unavailable",
        ) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("keys"), list):
        raise AppError(
            "Google token verification is currently unavailable",
            503,
            code="oauth_verification_unavailable",
        )
    return payload


def verify_google_id_token(credential: str) -> dict[str, Any]:
    """Verify a Google ID token's signature, audience, issuer, expiry and email.

    The JWKS fetch is a separate function so tests can replace it with a local
    RSA key and never touch the network.
    """
    if not settings.GOOGLE_OAUTH_CLIENT_ID:
        raise AppError("Google OAuth is not configured", 503, code="oauth_not_configured")

    try:
        header = jwt.get_unverified_header(credential)
    except jwt.PyJWTError as exc:
        raise _invalid_token() from exc
    kid = header.get("kid")
    jwks = _fetch_google_jwks()
    matching = [key for key in jwks.get("keys", []) if key.get("kid") == kid] if kid else []
    if not matching:
        raise _invalid_token()

    claims: dict[str, Any] | None = None
    last_error: jwt.PyJWTError | None = None
    for key_data in matching:
        try:
            public_key = RSAAlgorithm.from_jwk(json.dumps(key_data))
            claims = jwt.decode(
                credential,
                key=public_key,
                algorithms=["RS256"],
                audience=settings.GOOGLE_OAUTH_CLIENT_ID,
                options={"require": ["exp", "aud", "iss", "sub", "email"]},
            )
            break
        except jwt.PyJWTError as exc:
            last_error = exc
    if claims is None:
        raise _invalid_token() from last_error

    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise _invalid_token()
    if claims.get("email_verified") is not True:
        raise _invalid_token()

    email = str(claims.get("email") or "").strip().lower()
    subject = str(claims.get("sub") or "")
    if not email or not subject:
        raise _invalid_token()

    # Normalise only the fields the rest of the flow relies on.
    return {**claims, "email": email, "sub": subject}


def get_or_create_google_user(db: Session, claims: dict[str, Any]) -> User:
    """Find a user by verified email, or create a student with an unusable password.

    New accounts never receive an admin/HOD/staff role from an external token.
    """
    email = claims["email"]
    subject = claims["sub"]
    user = db.scalar(select(User).where(User.email == email))

    if user is None:
        display_name = str(claims.get("name") or email.split("@")[0]).strip()[:120]
        user = User(
            full_name=display_name or email[:120],
            email=email[:255],
            password_hash=hash_password(secrets.token_urlsafe(48)),
            role=UserRole.STUDENT.value,
            department_id=None,
            is_active=True,
        )
        db.add(user)
        db.flush()
    elif not user.is_active:
        raise AppError("This account is inactive", 401, code="inactive_account")

    link = db.scalar(
        select(UserOauthAccount).where(
            UserOauthAccount.provider == "google",
            UserOauthAccount.provider_subject == subject,
        )
    )
    if link is None:
        db.add(
            UserOauthAccount(
                user_id=user.id,
                provider="google",
                provider_subject=subject,
                provider_email=email[:255],
                linked_at=datetime.now(timezone.utc),
            )
        )
    else:
        link.user_id = user.id
        link.provider_email = email[:255]
    db.flush()
    return user
