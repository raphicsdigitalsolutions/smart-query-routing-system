"""Notification composition, persistence and best-effort outward delivery.

Only public messages and approved state changes reach this module. Internal
staff notes and unapproved AI drafts are never rendered into a notification
body, and internal notes do not produce notification rows at all.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Notification, Ticket, User
from app.services import email as email_service
from app.services import whatsapp as whatsapp_service

# Stable event identifiers stored on notification rows.
TICKET_CREATED = "ticket.created"
TICKET_ASSIGNED = "ticket.assigned"
PUBLIC_REPLY = "public.reply"
AUTO_REPLY = "assignment.auto_reply"
TICKET_ESCALATED = "ticket.escalated_automatically"
TICKET_RESOLVED = "ticket.resolved"
TICKET_CLOSED = "ticket.closed"

_DEDUPE_WINDOW_MINUTES = 10
_EVENT_LABELS = {
    TICKET_CREATED: "New ticket",
    TICKET_ASSIGNED: "Ticket assigned",
    PUBLIC_REPLY: "New public reply",
    AUTO_REPLY: "Automatic absence reply",
    TICKET_ESCALATED: "Ticket escalated",
    TICKET_RESOLVED: "Ticket resolved",
    TICKET_CLOSED: "Ticket closed",
}
_FOOTER = (
    "---\nAutomated notification from the Smart Query Routing System. "
    "Please do not reply to this message."
)


def utc_now() -> datetime:
    """Naive UTC timestamp matching the project's SQLite timestamp storage."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def render_notification_body(
    ticket: Ticket,
    event_type: str,
    *,
    actor: User | None = None,
    public_message: str | None = None,
    resolution_summary: str | None = None,
) -> str:
    """Build a professional plain-text body with no internal/draft content."""
    lines = [
        "Smart Query Routing System",
        "",
        f"Ticket reference: {ticket.public_reference}",
        f"Subject: {ticket.subject}",
        f"Update: {_EVENT_LABELS.get(event_type, event_type)}",
    ]
    if actor is not None and getattr(actor, "full_name", None):
        lines.append(f"Actor: {actor.full_name}")
    if resolution_summary:
        lines += ["", "Resolution summary:", str(resolution_summary).strip()]
    if public_message:
        lines += ["", str(public_message).strip()]
    lines += [
        "",
        f"Open ticket: /tickets/{ticket.id}",
        "",
        _FOOTER,
    ]
    return "\n".join(lines)


def _dedupe_recipients(recipients: Iterable[User]) -> list[User]:
    seen: dict[int, User] = {}
    for user in recipients:
        if user is None or not getattr(user, "is_active", True):
            continue
        seen.setdefault(user.id, user)
    return list(seen.values())


def _recent_delivery_exists(
    db: Session,
    *,
    ticket_id: int,
    event_type: str,
    recipient_user_id: int,
    channel: str,
    now: datetime,
) -> bool:
    """Deterministic idempotency guard for outward delivery rows."""
    cutoff = now - timedelta(minutes=_DEDUPE_WINDOW_MINUTES)
    return (
        db.scalar(
            select(Notification.id)
            .where(
                Notification.ticket_id == ticket_id,
                Notification.event_type == event_type,
                Notification.recipient_user_id == recipient_user_id,
                Notification.channel == channel,
                Notification.created_at >= cutoff,
            )
            .limit(1)
        )
        is not None
    )


def _add_row(
    db: Session,
    *,
    ticket: Ticket,
    recipient: User,
    channel: str,
    event_type: str,
    subject: str,
    body: str,
    address: str | None,
    now: datetime,
    status: str,
) -> Notification:
    row = Notification(
        ticket_id=ticket.id,
        recipient_user_id=recipient.id,
        recipient_address=address,
        channel=channel,
        event_type=event_type,
        subject=subject[:255],
        body=body,
        status=status,
        attempts=1 if status == "sent" else 0,
        sent_at=now if status == "sent" else None,
        is_internal=False,
    )
    db.add(row)
    db.flush()
    return row


def notify_ticket_event(
    db: Session,
    *,
    ticket: Ticket,
    event_type: str,
    recipients: Iterable[User],
    subject: str,
    actor: User | None = None,
    public_message: str | None = None,
    resolution_summary: str | None = None,
    address_overrides: dict[int, str] | None = None,
    channels: tuple[str, ...] = ("in_app", "email", "whatsapp"),
) -> list[Notification]:
    """Persist in-app rows and best-effort email/WhatsApp rows for an event.

    Callers own the surrounding transaction; this function only flushes.
    """
    body = render_notification_body(
        ticket,
        event_type,
        actor=actor,
        public_message=public_message,
        resolution_summary=resolution_summary,
    )
    now = utc_now()
    overrides = address_overrides or {}
    created: list[Notification] = []

    for recipient in _dedupe_recipients(recipients):
        if "in_app" in channels:
            created.append(
                _add_row(
                    db,
                    ticket=ticket,
                    recipient=recipient,
                    channel="in_app",
                    event_type=event_type,
                    subject=subject,
                    body=body,
                    address=None,
                    now=now,
                    status="sent",
                )
            )

        if "email" in channels and recipient.email and email_service.is_configured():
            if not _recent_delivery_exists(
                db,
                ticket_id=ticket.id,
                event_type=event_type,
                recipient_user_id=recipient.id,
                channel="email",
                now=now,
            ):
                address = overrides.get(recipient.id) or recipient.email
                row = _add_row(
                    db,
                    ticket=ticket,
                    recipient=recipient,
                    channel="email",
                    event_type=event_type,
                    subject=subject,
                    body=body,
                    address=address,
                    now=now,
                    status="pending",
                )
                result = email_service.send_email(
                    to_address=address, subject=subject, body=body
                )
                row.attempts = result.attempts
                if result.ok:
                    row.status = "sent"
                    row.sent_at = utc_now()
                    row.provider_id = result.provider_id
                else:
                    row.status = "failed"
                    row.last_error = (result.error or "SMTP delivery failed")[:2000]
                created.append(row)

        if (
            "whatsapp" in channels
            and whatsapp_service.is_configured()
            and overrides.get(recipient.id)
        ):
            if not _recent_delivery_exists(
                db,
                ticket_id=ticket.id,
                event_type=event_type,
                recipient_user_id=recipient.id,
                channel="whatsapp",
                now=now,
            ):
                phone = overrides[recipient.id]
                row = _add_row(
                    db,
                    ticket=ticket,
                    recipient=recipient,
                    channel="whatsapp",
                    event_type=event_type,
                    subject=subject,
                    body=body,
                    address=phone,
                    now=now,
                    status="pending",
                )
                result = whatsapp_service.send_whatsapp(to_phone=phone, body=body)
                row.attempts = result.attempts
                if result.ok:
                    row.status = "sent"
                    row.sent_at = utc_now()
                    row.provider_id = result.provider_id
                else:
                    row.status = "failed"
                    row.last_error = (result.error or "WhatsApp delivery failed")[:2000]
                created.append(row)

    return created


def list_notifications(
    db: Session, *, user: User, skip: int = 0, limit: int = 20
) -> dict[str, Any]:
    conditions = [Notification.recipient_user_id == user.id]
    total = db.scalar(select(func.count(Notification.id)).where(*conditions)) or 0
    rows = db.scalars(
        select(Notification)
        .where(*conditions)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset(skip)
        .limit(limit)
    ).all()
    return {"items": list(rows), "total": total, "skip": skip, "limit": limit}


def mark_notification_read(db: Session, *, notification_id: int, user: User) -> Notification:
    row = db.get(Notification, notification_id)
    if row is None or row.recipient_user_id != user.id:
        raise NotFoundError("Notification")
    if row.read_at is None:
        row.read_at = utc_now()
    db.commit()
    db.refresh(row)
    return row
