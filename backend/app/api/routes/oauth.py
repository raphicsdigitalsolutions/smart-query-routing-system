"""Passwordless Google sign-in, returning the same token shape as /auth/login."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import create_access_token
from app.db.dependencies import get_db
from app.schemas.auth import LoginResponse, UserResponse
from app.schemas.oauth import GoogleCredentialRequest
from app.services import oauth_google
from app.services.audit import record_audit

router = APIRouter(prefix="/auth", tags=["auth", "oauth"])


@router.post("/google", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def google_login(
    payload: GoogleCredentialRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    if not settings.GOOGLE_OAUTH_ENABLED:
        raise AppError("Google sign-in is not configured", 503, code="oauth_not_configured")

    claims = oauth_google.verify_google_id_token(payload.credential)
    user = oauth_google.get_or_create_google_user(db, claims)
    token, expires_in = create_access_token(user.id, user.role)
    record_audit(
        db,
        actor=user,
        action="auth.google_login",
        entity_type="user",
        entity_id=user.id,
        details={"provider": "google", "email": user.email},
    )
    db.commit()
    db.refresh(user)
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )
