"""Authenticated notification centre endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.dependencies import get_db
from app.models import User
from app.schemas.notifications import (
    NotificationListResponse,
    NotificationMarkReadResponse,
    NotificationResponse,
)
from app.services.notifications import list_notifications, mark_notification_read

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
def get_notifications(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationListResponse:
    result = list_notifications(db, user=user, skip=skip, limit=limit)
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(row) for row in result["items"]],
        total=result["total"],
        skip=result["skip"],
        limit=result["limit"],
    )


@router.post("/{notification_id}/read", response_model=NotificationMarkReadResponse)
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationMarkReadResponse:
    row = mark_notification_read(db, notification_id=notification_id, user=user)
    return NotificationMarkReadResponse(notification=NotificationResponse.model_validate(row))
