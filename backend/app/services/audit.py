"""Central audit-log writer and admin-only reader."""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.models import AuditLog, User
from app.schemas.audit import AuditLogListResponse, AuditLogResponse

OVERRIDE_ACTIONS = {
    "ticket.assigned",
    "ticket.status_changed",
    "ticket.updated",
    "ticket.escalated",
    "ticket.deescalated",
}


def record_audit(
    db: Session,
    *,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: int | str,
    details: dict[str, Any] | None = None,
    is_override: bool | None = None,
    actor_role: str | None = None,
) -> AuditLog:
    """Append an audit entry (caller controls the surrounding transaction)."""
    resolved_role = actor_role or (actor.role if actor is not None else None)
    if is_override is None:
        is_override = (
            resolved_role in {UserRole.HOD.value, UserRole.ADMIN.value}
            and action in OVERRIDE_ACTIONS
        )

    entry = AuditLog(
        actor_id=actor.id if actor is not None else None,
        actor_role=resolved_role,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details,
        is_override=bool(is_override),
    )
    db.add(entry)
    return entry


def list_audit_logs(
    db: Session,
    *,
    actor_id: int | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = 0,
    limit: int = 50,
) -> AuditLogListResponse:
    """Return real audit rows (newest first) with the actor's email when present."""
    conditions: list[Any] = []
    if actor_id is not None:
        conditions.append(AuditLog.actor_id == actor_id)
    if action:
        conditions.append(AuditLog.action == action)
    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type)
    if entity_id:
        conditions.append(AuditLog.entity_id == str(entity_id))
    if date_from is not None:
        conditions.append(AuditLog.created_at >= date_from)
    if date_to is not None:
        conditions.append(AuditLog.created_at <= date_to)

    total = db.scalar(select(func.count(AuditLog.id)).where(*conditions)) or 0
    rows = db.execute(
        select(AuditLog, User.email.label("actor_email"))
        .outerjoin(User, AuditLog.actor_id == User.id)
        .where(*conditions)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()

    items = [
        AuditLogResponse(
            id=log.id,
            actor_id=log.actor_id,
            actor_email=actor_email,
            actor_role=log.actor_role,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
            is_override=log.is_override,
            created_at=log.created_at,
        )
        for log, actor_email in rows
    ]
    return AuditLogListResponse(items=items, total=int(total), skip=skip, limit=limit)
