"""Authenticated settings endpoints for per-user OpenAI credentials."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.dependencies import get_db
from app.models import User
from app.schemas.byok import ApiKeyStatusResponse, ApiKeyUpdate
from app.services import byok

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/api-keys", response_model=ApiKeyStatusResponse)
def get_api_key_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyStatusResponse:
    """Return key metadata only; the secret is never part of the response."""
    return byok.get_api_key_status(db, user.id)


@router.put("/api-keys", response_model=ApiKeyStatusResponse)
def replace_api_key(
    payload: ApiKeyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyStatusResponse:
    """Validate the provider key before encrypting and replacing any stored key."""
    return byok.save_api_key(db, user.id, payload.api_key)


@router.post("/api-keys/validate", response_model=ApiKeyStatusResponse)
def validate_api_key(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyStatusResponse:
    """Re-check the stored key with the provider and refresh its validity flag."""
    return byok.validate_api_key(db, user.id)


@router.delete("/api-keys", response_model=ApiKeyStatusResponse)
def delete_api_key(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApiKeyStatusResponse:
    """Remove the authenticated user's stored key."""
    return byok.delete_api_key(db, user.id)
