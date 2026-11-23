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


def test_manual_escalation_and_deescalation_record_history_audit_and_notifications(
    client, db_session, users, departments
) -> None:
    """Manual escalation and de-escalation must record history, audit and permission-scoped notifications."""
    created = client.post(
        BASE,
        json={
            "subject": "Java assignment escalation check",
            "description": "Ticket used to verify manual escalation history and notifications.",
            "department_id": departments["registry"].id,
        },
        headers=auth_header(client, users["student"].email),
    )
    assert created.status_code == 201, created.text
    ticket_id = created.json()["id"]

    # Assign to staff (leaving staff2 unassigned in the same department, and hod_other in another department)
    assigned = client.post(
        f"{BASE}/{ticket_id}/assign",
        json={"assignee_id": users["staff"].id},
        headers=auth_header(client, users["hod"].email),
    )
    assert assigned.status_code == 200, assigned.text

    hod_headers = auth_header(client, users["hod"].email)
    staff_headers = auth_header(client, users["staff"].email)
    staff2_headers = auth_header(client, users["staff2"].email)
    student_headers = auth_header(client, users["student"].email)
    other_hod_headers = auth_header(client, users["hod_other"].email)

    # Non-managers cannot escalate
    assert (
        client.patch(f"{BASE}/{ticket_id}", json={"is_escalated": True}, headers=student_headers).status_code
        == 403
    )
    assert (
        client.patch(f"{BASE}/{ticket_id}", json={"is_escalated": True}, headers=staff_headers).status_code
        == 403
    )
    assert (
        client.patch(f"{BASE}/{ticket_id}", json={"is_escalated": True}, headers=other_hod_headers).status_code
        == 404
    )

    # 1. HOD manually escalates
    escalated = client.patch(
        f"{BASE}/{ticket_id}",
        json={"is_escalated": True},
        headers=hod_headers,
    )
    assert escalated.status_code == 200, escalated.text
    esc_ticket = escalated.json()["ticket"]
    assert esc_ticket["is_escalated"] is True
    assert esc_ticket["escalated_at"] is not None

    # Repeat same-value escalation must not create duplicate rows
    noop = client.patch(
        f"{BASE}/{ticket_id}",
        json={"is_escalated": True},
        headers=hod_headers,
    )
    assert noop.status_code == 400
    assert noop.json()["code"] == "empty_update"

    # Verify AuditLog records actor, timestamp and previous/new values
    esc_audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == str(ticket_id),
            AuditLog.action == "ticket.escalated",
        )
    )
    assert esc_audit is not None
    assert esc_audit.actor_id == users["hod"].id
    assert esc_audit.actor_role == "hod"
    assert esc_audit.is_override is True
    assert esc_audit.details["previous_is_escalated"] is False
    assert esc_audit.details["new_is_escalated"] is True
    assert esc_audit.details["previous_escalated_at"] is None
    assert esc_audit.details["new_escalated_at"] is not None

    # Verify TicketStatusHistory + /history endpoint
    history_resp = client.get(f"{BASE}/{ticket_id}/history", headers=hod_headers)
    assert history_resp.status_code == 200, history_resp.text
    history_json = history_resp.json()
    assert len(history_json["escalations"]) == 1
    esc_event = history_json["escalations"][0]
    assert esc_event["action"] == "escalated"
    assert esc_event["from_escalated"] is False
    assert esc_event["to_escalated"] is True
    assert esc_event["actor_id"] == users["hod"].id
    assert esc_event["actor_name"] == users["hod"].full_name
    assert esc_event["actor_role"] == "hod"
    assert esc_event["mode"] == "manual"
    assert any(
        item["changed_by_id"] == users["hod"].id and "not escalated -> escalated" in (item["note"] or "")
        for item in history_json["status_changes"]
    )

    # Verify escalation notification fanout without duplicates and obeying permissions
    esc_notifs = db_session.scalars(
        select(Notification).where(
            Notification.ticket_id == ticket_id,
            Notification.event_type == "ticket.escalated",
            Notification.channel == "in_app",
        )
    ).all()
    recipient_ids = [row.recipient_user_id for row in esc_notifs]
    assert len(recipient_ids) == len(set(recipient_ids)), "Duplicate escalation notifications created"
    assert set(recipient_ids) == {
        users["staff"].id,
        users["hod"].id,
        users["admin"].id,
    }
    # Unassigned same-dept staff (staff2) and other-dept HOD (hod_other) cannot view ticket and must not be notified
    assert users["staff2"].id not in recipient_ids
    assert users["hod_other"].id not in recipient_ids
    assert client.get(f"{BASE}/{ticket_id}", headers=staff2_headers).status_code == 404

    # Notification centre API returns the escalation notification to assigned staff and HOD
    staff_inbox = client.get("/api/v1/notifications", headers=staff_headers).json()["items"]
    hod_inbox = client.get("/api/v1/notifications", headers=hod_headers).json()["items"]
    assert any(item["ticket_id"] == ticket_id and item["event_type"] == "ticket.escalated" for item in staff_inbox)
    assert any(item["ticket_id"] == ticket_id and item["event_type"] == "ticket.escalated" for item in hod_inbox)

    # 2. De-escalate the ticket and verify history, audit, and notification
    deescalated = client.patch(
        f"{BASE}/{ticket_id}",
        json={"is_escalated": False},
        headers=auth_header(client, users["admin"].email),
    )
    assert deescalated.status_code == 200, deescalated.text
    assert deescalated.json()["ticket"]["is_escalated"] is False
    assert deescalated.json()["ticket"]["escalated_at"] is None

    deesc_audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == str(ticket_id),
            AuditLog.action == "ticket.deescalated",
        )
    )
    assert deesc_audit is not None
    assert deesc_audit.actor_id == users["admin"].id
    assert deesc_audit.is_override is True
    assert deesc_audit.details["previous_is_escalated"] is True
    assert deesc_audit.details["new_is_escalated"] is False
    assert deesc_audit.details["previous_escalated_at"] is not None
    assert deesc_audit.details["new_escalated_at"] is None

    history_after = client.get(f"{BASE}/{ticket_id}/history", headers=hod_headers).json()
    assert [(item["from_escalated"], item["to_escalated"], item["action"]) for item in history_after["escalations"]] == [
        (False, True, "escalated"),
        (True, False, "deescalated"),
    ]
    assert any(
        item["changed_by_id"] == users["admin"].id and "escalated -> not escalated" in (item["note"] or "")
        for item in history_after["status_changes"]
    )

    deesc_notifs = db_session.scalars(
        select(Notification).where(
            Notification.ticket_id == ticket_id,
            Notification.event_type == "ticket.deescalated",
            Notification.channel == "in_app",
        )
    ).all()
    assert {row.recipient_user_id for row in deesc_notifs} == {
        users["staff"].id,
        users["hod"].id,
        users["admin"].id,
    }


def test_escalation_notifications_deduplicate_when_assignee_is_hod(
    client, db_session, users, departments
) -> None:
    """When a ticket is assigned to the department HOD, escalation notifies the HOD once, not twice."""
    created = client.post(
        BASE,
        json={
            "subject": "HOD self-assigned ticket escalation dedupe check",
            "description": "Verifies no duplicate notifications are generated when assignee is also HOD.",
            "department_id": departments["registry"].id,
        },
        headers=auth_header(client, users["student"].email),
    )
    ticket_id = created.json()["id"]
    assert (
        client.post(
            f"{BASE}/{ticket_id}/assign",
            json={"assignee_id": users["hod"].id},
            headers=auth_header(client, users["admin"].email),
        ).status_code
        == 200
    )

    resp = client.patch(
        f"{BASE}/{ticket_id}",
        json={"is_escalated": True},
        headers=auth_header(client, users["admin"].email),
    )
    assert resp.status_code == 200, resp.text

    notifs = db_session.scalars(
        select(Notification).where(
            Notification.ticket_id == ticket_id,
            Notification.event_type == "ticket.escalated",
            Notification.channel == "in_app",
        )
    ).all()
    recipients = [row.recipient_user_id for row in notifs]
    assert len(recipients) == len(set(recipients))
    assert set(recipients) == {users["hod"].id, users["admin"].id}
    assert recipients.count(users["hod"].id) == 1
