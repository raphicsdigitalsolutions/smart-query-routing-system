"""User lookup for ticket assignment screens."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.dependencies import get_db
from app.models import User
from app.schemas.ticket import AssignableUserListResponse
from app.services.tickets import list_assignable_users

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/assignable", response_model=AssignableUserListResponse)
def get_assignable_users(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssignableUserListResponse:
    return list_assignable_users(db, user)
