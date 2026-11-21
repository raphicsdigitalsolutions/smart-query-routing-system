"""Reproducible SLA escalation tests with deterministic timestamps."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.models import AuditLog, Notification, Ticket, TicketStatusHistory
from app.services.escalation import run_escalation_sweep
from tests.conftest import auth_header

BASE = "/api/v1/tickets"


def _make_old_ticket(client, db_session, users, departments, *, hours_old=30):
    response = client.post(
        BASE,
        json={
            "subject": "Escalation sweep candidate",
            "description": "This request has been waiting far too long for a reply.",
            "department_id": departments["registry"].id,
        },
        headers=auth_header(client, users["student"].email),
    )
    assert response.status_code == 201, response.text
    ticket_id = response.json()["id"]
    old = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours_old)
    db_session.execute(update(Ticket).where(Ticket.id == ticket_id).values(created_at=old))
    db_session.commit()
    return ticket_id


def test_sweep_escalates_once_audits_and_notifies_all_participants(
    client, db_session, users, departments
) -> None:
    ticket_id = _make_old_ticket(client, db_session, users, departments)
    client.post(
        f"{BASE}/{ticket_id}/assign",
        json={"assignee_id": users["staff"].id},
        headers=auth_header(client, users["admin"].email),
    )
    now = datetime.now(timezone.utc)

    first = run_escalation_sweep(db_session, now=now, hours=24)
    assert first == {"scanned": 1, "escalated": 1}

    ticket = db_session.get(Ticket, ticket_id)
    assert ticket.is_escalated is True
    assert ticket.escalated_at is not None
    assert ticket.status not in {"resolved", "closed"}

    history = db_session.scalars(
        select(TicketStatusHistory).where(TicketStatusHistory.ticket_id == ticket_id)
    ).all()
    assert any("Automatically escalated" in (row.note or "") for row in history)

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == str(ticket_id),
            AuditLog.action == "ticket.escalated_automatically",
        )
    )
    assert audit is not None

    notifications = db_session.scalars(
        select(Notification).where(
            Notification.ticket_id == ticket_id,
            Notification.event_type == "ticket.escalated_automatically",
            Notification.channel == "in_app",
        )
    ).all()
    assert {row.recipient_user_id for row in notifications} == {
        users["student"].id,
        users["staff"].id,
        users["hod"].id,
        users["admin"].id,
    }


def test_sweep_is_repeat_safe(client, db_session, users, departments) -> None:
    ticket_id = _make_old_ticket(client, db_session, users, departments)
    now = datetime.now(timezone.utc)
    assert run_escalation_sweep(db_session, now=now, hours=24) == {"scanned": 1, "escalated": 1}
    assert run_escalation_sweep(db_session, now=now, hours=24) == {"scanned": 0, "escalated": 0}
    assert db_session.get(Ticket, ticket_id).is_escalated is True


def test_recent_tickets_are_not_escalated(client, db_session, users, departments) -> None:
    client.post(
        BASE,
        json={
            "subject": "Fresh ticket should not escalate",
            "description": "This request was submitted just now and is still fresh.",
            "department_id": departments["registry"].id,
        },
        headers=auth_header(client, users["student"].email),
    )
    result = run_escalation_sweep(db_session, now=datetime.now(timezone.utc), hours=24)
    assert result == {"scanned": 0, "escalated": 0}


def test_escalation_run_endpoint_is_admin_only(client, db_session, users, departments) -> None:
    _make_old_ticket(client, db_session, users, departments)
    url = f"{BASE}/escalation/run"

    denied = client.post(url, headers=auth_header(client, users["staff"].email))
    assert denied.status_code == 403
    assert denied.json()["code"] == "forbidden"

    allowed = client.post(url, headers=auth_header(client, users["admin"].email))
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["escalated"] == 1
