"""Instructor leave windows and their auto-reply text."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_staff_or_above
from app.db.dependencies import get_db
from app.models import User
from app.schemas.leave import (
    LeaveCreate,
    LeaveListResponse,
    LeaveMutationResponse,
    LeaveUpdate,
)
from app.services.leave import (
    create_leave,
    deactivate_leave,
    list_leave,
    update_leave,
)

router = APIRouter(prefix="/leave", tags=["leave"])


@router.get("", response_model=LeaveListResponse)
def get_leave(
    db: Session = Depends(get_db),
    user: User = Depends(require_staff_or_above),
) -> LeaveListResponse:
    """Own windows for staff, department windows for HOD, all for admin."""
    return list_leave(db, user)


@router.post("", response_model=LeaveMutationResponse, status_code=status.HTTP_201_CREATED)
def post_leave(
    payload: LeaveCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff_or_above),
) -> LeaveMutationResponse:
    return create_leave(db, payload, user)


@router.patch("/{leave_id}", response_model=LeaveMutationResponse)
def patch_leave(
    leave_id: int,
    payload: LeaveUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff_or_above),
) -> LeaveMutationResponse:
    return update_leave(db, leave_id, payload, user)


@router.delete("/{leave_id}", response_model=LeaveMutationResponse)
def delete_leave(
    leave_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff_or_above),
) -> LeaveMutationResponse:
    return deactivate_leave(db, leave_id, user)
