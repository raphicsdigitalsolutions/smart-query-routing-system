"""Admin-managed, role/department-scoped announcements."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.dependencies import get_db
from app.models import User
from app.schemas.announcements import (
    AnnouncementCreate,
    AnnouncementListResponse,
    AnnouncementResponse,
    AnnouncementUpdate,
)
from app.services.announcements import (
    create_announcement,
    deactivate_announcement,
    list_announcements,
    update_announcement,
)

router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("", response_model=AnnouncementListResponse)
def get_announcements(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AnnouncementListResponse:
    """Only active broadcasts targeted at the caller's role and department."""
    return list_announcements(db, user)


@router.post("", response_model=AnnouncementResponse, status_code=status.HTTP_201_CREATED)
def post_announcement(
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AnnouncementResponse:
    return create_announcement(db, payload, admin)


@router.patch("/{announcement_id}", response_model=AnnouncementResponse)
def patch_announcement(
    announcement_id: int,
    payload: AnnouncementUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AnnouncementResponse:
    return update_announcement(db, announcement_id, payload, admin)


@router.delete("/{announcement_id}", response_model=AnnouncementResponse)
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AnnouncementResponse:
    """Soft-deactivation: the row stays for the audit trail but is not visible."""
    return deactivate_announcement(db, announcement_id, admin)
