"""Admin-managed broadcasts with role/department audience scoping."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.errors import AppError, NotFoundError
from app.models import Announcement, Department, User
from app.schemas.announcements import (
    AnnouncementCreate,
    AnnouncementListResponse,
    AnnouncementResponse,
    AnnouncementUpdate,
)
from app.services.audit import record_audit


def _response(row: Announcement) -> AnnouncementResponse:
    return AnnouncementResponse(
        id=row.id,
        title=row.title,
        body=row.body,
        audience_roles=list(row.audience_roles_json or []),
        department_id=row.department_id,
        created_by_id=row.created_by_id,
        published_at=row.published_at,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _role_strings(values: list[UserRole] | list[str]) -> list[str]:
    return [value.value if isinstance(value, UserRole) else str(value) for value in values]


def _get_announcement(db: Session, announcement_id: int) -> Announcement:
    row = db.get(Announcement, announcement_id)
    if row is None:
        raise NotFoundError("Announcement")
    return row


def _validate_department(db: Session, department_id: int | None) -> None:
    if department_id is None:
        return
    if db.get(Department, department_id) is None:
        raise NotFoundError("Department")


def list_announcements(db: Session, user: User) -> AnnouncementListResponse:
    """Active announcements whose audience includes the caller.

    A null department means "all departments"; a set department only matches
    users assigned to it. The role check is applied to the stored JSON list.
    """
    rows = db.scalars(
        select(Announcement)
        .where(Announcement.is_active.is_(True))
        .order_by(Announcement.published_at.desc(), Announcement.id.desc())
    ).all()
    visible = [
        row
        for row in rows
        if user.role in (row.audience_roles_json or [])
        and (row.department_id is None or row.department_id == user.department_id)
    ]
    return AnnouncementListResponse(
        items=[_response(row) for row in visible],
        total=len(visible),
    )


def create_announcement(db: Session, payload: AnnouncementCreate, actor: User) -> AnnouncementResponse:
    _validate_department(db, payload.department_id)
    now = datetime.now(timezone.utc)
    row = Announcement(
        title=payload.title,
        body=payload.body,
        audience_roles_json=_role_strings(payload.audience_roles),
        department_id=payload.department_id,
        created_by_id=actor.id,
        is_active=payload.is_active,
        published_at=now if payload.is_active else None,
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action="announcement.created",
        entity_type="announcement",
        entity_id=row.id,
        details={"title": row.title, "audience_roles": row.audience_roles_json},
    )
    db.commit()
    db.refresh(row)
    return _response(row)


def update_announcement(
    db: Session, announcement_id: int, payload: AnnouncementUpdate, actor: User
) -> AnnouncementResponse:
    row = _get_announcement(db, announcement_id)
    supplied: dict[str, Any] = payload.model_dump(exclude_unset=True)
    if not supplied:
        raise AppError("No changes supplied", 400, code="empty_update")
    was_active = row.is_active

    if "department_id" in supplied:
        _validate_department(db, supplied["department_id"])

    field_map = {
        "title": "title",
        "body": "body",
        "audience_roles": "audience_roles_json",
        "department_id": "department_id",
        "is_active": "is_active",
    }
    for key, column in field_map.items():
        if key in supplied:
            value = supplied[key]
            setattr(row, column, _role_strings(value) if key == "audience_roles" else value)

    if "is_active" in supplied and row.is_active and not was_active:
        row.published_at = datetime.now(timezone.utc)
    if was_active and not row.is_active:
        record_audit(
            db,
            actor=actor,
            action="announcement.deactivated",
            entity_type="announcement",
            entity_id=row.id,
            details={"title": row.title},
        )
    changed_fields = [key for key in supplied if not (key == "is_active" and was_active and not row.is_active)]
    if changed_fields:
        record_audit(
            db,
            actor=actor,
            action="announcement.updated",
            entity_type="announcement",
            entity_id=row.id,
            details={"fields": sorted(changed_fields)},
        )

    db.commit()
    db.refresh(row)
    return _response(row)


def deactivate_announcement(db: Session, announcement_id: int, actor: User) -> AnnouncementResponse:
    """DELETE is a soft deactivation so the audit history stays meaningful."""
    row = _get_announcement(db, announcement_id)
    if row.is_active:
        row.is_active = False
        record_audit(
            db,
            actor=actor,
            action="announcement.deactivated",
            entity_type="announcement",
            entity_id=row.id,
            details={"title": row.title, "via": "delete"},
        )
        db.commit()
        db.refresh(row)
    return _response(row)
