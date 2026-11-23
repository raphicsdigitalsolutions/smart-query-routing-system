"""Deterministic 24-hour SLA escalation sweep."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Ticket, TicketStatusHistory
from app.services.audit import record_audit
from app.services.notifications import TICKET_ESCALATED, notify_ticket_event
from app.services.tickets import escalation_recipients

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
        previous_escalated = bool(ticket.is_escalated)
        previous_escalated_at = ticket.escalated_at
        ticket.is_escalated = True
        ticket.escalated_at = reference
        note = f"Automatically escalated after {window_hours}h SLA"
        db.add(
            TicketStatusHistory(
                ticket_id=ticket.id,
                from_status=ticket.status,
                to_status=ticket.status,
                changed_by_id=None,
                note=note,
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
                "previous_is_escalated": previous_escalated,
                "new_is_escalated": True,
                "previous_escalated_at": (
                    previous_escalated_at.isoformat() if previous_escalated_at else None
                ),
                "new_escalated_at": reference.isoformat(),
                "actor_name": "System (SLA)",
                "mode": "automatic",
                "note": note,
            },
            is_override=False,
        )

        recipients = escalation_recipients(db, ticket, include_student=True)

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
