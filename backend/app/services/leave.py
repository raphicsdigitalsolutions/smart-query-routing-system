"""Instructor leave windows and the auto-reply lookup used by the reply worker."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import false, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models import InstructorLeave, User
from app.schemas.leave import (
    LeaveCreate,
    LeaveListResponse,
    LeaveMutationResponse,
    LeaveResponse,
    LeaveUpdate,
)
from app.services.audit import record_audit


def _forbidden() -> AppError:
    return AppError("You do not have permission for this leave window", 403, code="forbidden")


def _validate_window(start_at: datetime, end_at: datetime) -> None:
    if start_at.tzinfo is None:
        start_at = start_at.replace(tzinfo=timezone.utc)
    if end_at.tzinfo is None:
        end_at = end_at.replace(tzinfo=timezone.utc)
    if end_at <= start_at:
        raise AppError("end_at must be after start_at", 400, code="invalid_leave_window")


def _response(db: Session, row: InstructorLeave) -> LeaveResponse:
    owner = db.get(User, row.user_id)
    return LeaveResponse(
        id=row.id,
        user_id=row.user_id,
        user_email=owner.email if owner else None,
        start_at=row.start_at,
        end_at=row.end_at,
        reason=row.reason,
        auto_reply=row.auto_reply,
        is_active=row.is_active,
        created_by_id=row.created_by_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _get_leave(db: Session, leave_id: int) -> InstructorLeave:
    row = db.get(InstructorLeave, leave_id)
    if row is None:
        raise NotFoundError("Leave")
    return row


def _department_user_ids(user: User):
    """A SELECT of user ids in the HOD's department (empty when unassigned)."""
    condition = false() if user.department_id is None else User.department_id == user.department_id
    return select(User.id).where(condition)


def _target_user(db: Session, user: User, requested_id: int | None) -> User:
    target = user if requested_id is None else db.get(User, requested_id)
    if target is None:
        raise NotFoundError("User")
    if not target.is_active:
        raise AppError("Target account is inactive", 400, code="inactive_user")
    if user.role == "staff" and target.id != user.id:
        raise _forbidden()
    if user.role == "hod" and (
        user.department_id is None or target.department_id != user.department_id
    ):
        raise _forbidden()
    return target


def _can_manage(user: User, row: InstructorLeave) -> bool:
    if user.role in {"admin", "hod"}:
        return True
    return user.role == "staff" and row.user_id == user.id


def active_auto_reply(db: Session, user_id: int, at: datetime | None = None) -> str | None:
    """Return the auto-reply text of an active window covering ``at``, else None.

    Other workers import this directly. The end bound is exclusive, so a reply
    stops applying exactly at ``end_at``.
    """
    moment = at or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    row = db.scalar(
        select(InstructorLeave)
        .where(
            InstructorLeave.user_id == user_id,
            InstructorLeave.is_active.is_(True),
            InstructorLeave.start_at <= moment,
            InstructorLeave.end_at > moment,
        )
        .order_by(InstructorLeave.start_at.desc(), InstructorLeave.id.desc())
    )
    return row.auto_reply if row else None


def list_leave(db: Session, user: User) -> LeaveListResponse:
    """Staff see their own windows, HODs their department, admins everything."""
    conditions: list[Any] = []
    if user.role == "staff":
        conditions.append(InstructorLeave.user_id == user.id)
    elif user.role == "hod":
        conditions.append(InstructorLeave.user_id.in_(_department_user_ids(user)))
    elif user.role != "admin":
        raise _forbidden()

    rows = db.scalars(
        select(InstructorLeave)
        .where(*conditions)
        .order_by(InstructorLeave.start_at.desc(), InstructorLeave.id.desc())
    ).all()
    return LeaveListResponse(
        items=[_response(db, row) for row in rows],
        total=len(rows),
    )


def create_leave(db: Session, payload: LeaveCreate, actor: User) -> LeaveMutationResponse:
    target = _target_user(db, actor, payload.user_id)
    _validate_window(payload.start_at, payload.end_at)
    row = InstructorLeave(
        user_id=target.id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        reason=payload.reason,
        auto_reply=payload.auto_reply,
        is_active=payload.is_active,
        created_by_id=actor.id,
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        actor=actor,
        action="leave.created",
        entity_type="leave",
        entity_id=row.id,
        details={"user_id": target.id, "start_at": str(row.start_at), "end_at": str(row.end_at)},
    )
    db.commit()
    db.refresh(row)
    return LeaveMutationResponse(leave=_response(db, row))


def update_leave(db: Session, leave_id: int, payload: LeaveUpdate, actor: User) -> LeaveMutationResponse:
    row = _get_leave(db, leave_id)
    if not _can_manage(actor, row):
        raise _forbidden()

    supplied: dict[str, Any] = payload.model_dump(exclude_unset=True)
    if not supplied:
        raise AppError("No changes supplied", 400, code="empty_update")
    if "user_id" in supplied:
        target = _target_user(db, actor, supplied["user_id"])
        supplied["user_id"] = target.id

    start_at = supplied.get("start_at", row.start_at)
    end_at = supplied.get("end_at", row.end_at)
    _validate_window(start_at, end_at)

    was_active = row.is_active
    for key in ("user_id", "start_at", "end_at", "reason", "auto_reply", "is_active"):
        if key in supplied and supplied[key] is not None:
            setattr(row, key, supplied[key])

    if was_active and not row.is_active:
        record_audit(
            db,
            actor=actor,
            action="leave.deactivated",
            entity_type="leave",
            entity_id=row.id,
            details={"user_id": row.user_id},
        )
    changed = [key for key in supplied if not (key == "is_active" and was_active and not row.is_active)]
    if changed:
        record_audit(
            db,
            actor=actor,
            action="leave.updated",
            entity_type="leave",
            entity_id=row.id,
            details={"fields": sorted(changed)},
        )

    db.commit()
    db.refresh(row)
    return LeaveMutationResponse(leave=_response(db, row))


def deactivate_leave(db: Session, leave_id: int, actor: User) -> LeaveMutationResponse:
    """DELETE is a soft deactivation so the audit trail remains intact."""
    row = _get_leave(db, leave_id)
    if not _can_manage(actor, row):
        raise _forbidden()
    if row.is_active:
        row.is_active = False
        record_audit(
            db,
            actor=actor,
            action="leave.deactivated",
            entity_type="leave",
            entity_id=row.id,
            details={"user_id": row.user_id, "via": "delete"},
        )
        db.commit()
        db.refresh(row)
    return LeaveMutationResponse(leave=_response(db, row), message="Leave deactivated")


__all__ = ["active_auto_reply"]
