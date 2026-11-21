"""Deterministic 24-hour SLA escalation sweep."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Ticket, TicketStatusHistory, User
from app.services.audit import record_audit
from app.services.notifications import TICKET_ESCALATED, notify_ticket_event

_TERMINAL_STATUSES = ("resolved", "closed")
_SYSTEM_ACTOR = SimpleNamespace(id=None, role="system")


def _naive_utc(value: datetime) -> datetime:
    """Normalize to naive UTC for cross-database timestamp comparisons."""
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def run_escalation_sweep(
    db: Session, *, now: datetime | None = None, hours: int | None = None
) -> dict[str, int]:
    """Escalate every open ticket older than the SLA window (repeat-safe)."""
    window_hours = hours if hours is not None else settings.SLA_HOURS
    reference = _naive_utc(now or datetime.now(timezone.utc))
    cutoff = reference - timedelta(hours=window_hours)

    candidates = db.scalars(
        select(Ticket)
        .where(
            Ticket.is_escalated.is_(False),
            Ticket.status.notin_(_TERMINAL_STATUSES),
            Ticket.created_at <= cutoff,
        )
        .order_by(Ticket.id)
    ).all()
    scanned = len(candidates)

    escalated = 0
    for ticket in candidates:
        ticket.is_escalated = True
        ticket.escalated_at = reference
        db.add(
            TicketStatusHistory(
                ticket_id=ticket.id,
                from_status=ticket.status,
                to_status=ticket.status,
                changed_by_id=None,
                note=f"Automatically escalated after {window_hours}h SLA",
            )
        )
        record_audit(
            db,
            actor=_SYSTEM_ACTOR,  # type: ignore[arg-type]
            action="ticket.escalated_automatically",
            entity_type="ticket",
            entity_id=ticket.id,
            details={
                "public_reference": ticket.public_reference,
                "sla_hours": window_hours,
            },
            is_override=False,
        )

        recipients: list[User] = []
        student = db.get(User, ticket.student_id)
        if student is not None:
            recipients.append(student)
        if ticket.assigned_to is not None:
            assignee = db.get(User, ticket.assigned_to)
            if assignee is not None:
                recipients.append(assignee)
        recipients.extend(
            db.scalars(
                select(User).where(
                    User.is_active.is_(True),
                    User.role == "hod",
                    User.department_id == ticket.department_id,
                )
            ).all()
        )
        recipients.extend(
            db.scalars(
                select(User).where(User.is_active.is_(True), User.role == "admin")
            ).all()
        )

        notify_ticket_event(
            db,
            ticket=ticket,
            event_type=TICKET_ESCALATED,
            recipients=recipients,
            subject=f"Escalated ticket {ticket.public_reference}",
            public_message=(
                f"This ticket exceeded the {window_hours}-hour SLA window and "
                "has been automatically escalated for priority review."
            ),
        )
        escalated += 1

    db.commit()
    return {"scanned": scanned, "escalated": escalated}
