"""Deterministic instructor routing and leave-aware exclusion tests."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import hash_password
from app.models import (
    AuditLog,
    InstructorLeave,
    Message,
    Notification,
    Ticket,
    TicketAssignmentHistory,
    TicketStatusHistory,
    User,
)
from app.services.notifications import AUTO_REPLY, TICKET_ASSIGNED, TICKET_CREATED
from tests.conftest import TEST_PASSWORD, auth_header

BASE = "/api/v1/tickets"
EMAIL_URL = "/api/v1/integrations/email/inbound"
WHATSAPP_URL = "/api/v1/integrations/whatsapp/inbound"


def _add_staff(
    db_session,
    departments,
    *,
    email: str,
    full_name: str,
    department_key: str = "registry",
    is_active: bool = True,
    role: str = "staff",
) -> User:
    row = User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(TEST_PASSWORD),
        role=role,
        department_id=departments[department_key].id if department_key else None,
        is_active=is_active,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _add_leave(db_session, users, staff: User, start_at: datetime, end_at: datetime) -> InstructorLeave:
    row = InstructorLeave(
        user_id=staff.id,
        start_at=start_at,
        end_at=end_at,
        reason="Annual leave",
        auto_reply="I am on leave; another instructor will respond.",
        is_active=True,
        created_by_id=users["admin"].id,
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    return row


def _add_assigned_ticket(
    db_session,
    users,
    departments,
    assignee: User,
    *,
    status: str = "assigned",
) -> Ticket:
    ticket = Ticket(
        public_reference=f"TKT-{secrets.token_hex(6).upper()}",
        subject="Existing assigned registry work",
        description="This existing assignment contributes to the instructor workload.",
        category="Registry",
        priority="normal",
        status=status,
        student_id=users["student"].id,
        assigned_to=assignee.id,
        department_id=departments["registry"].id,
        channel="web",
        auto_routed=False,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket


def _resolve_instructor(db_session, *, department_id: int, at: datetime | None = None):
    from app.services.instructor_routing import resolve_instructor

    return resolve_instructor(db_session, department_id=department_id, at=at)


def _submit_auto(client, users, departments, **overrides):
    email = overrides.pop("student_email", users["student"].email)
    payload = {
        "subject": "Registry records correction request",
        "description": "Please correct the student records entry for this term.",
        "department_id": None,
        "auto_route": True,
        "priority": "normal",
    }
    payload.update(overrides)
    return client.post(BASE, json=payload, headers=auth_header(client, email))


def _notification_rows(db_session, *, ticket_id: int, recipient_id: int, event_type: str):
    return db_session.scalars(
        select(Notification).where(
            Notification.ticket_id == ticket_id,
            Notification.recipient_user_id == recipient_id,
            Notification.event_type == event_type,
        )
    ).all()


# --- Unit tests for deterministic selection ---------------------------------


def test_resolve_instructor_selects_active_staff_in_resolved_department(
    db_session, users, departments
) -> None:
    users["staff2"].is_active = False
    db_session.commit()

    decision = _resolve_instructor(db_session, department_id=departments["registry"].id)

    assert decision.instructor is not None
    assert decision.instructor.id == users["staff"].id
    assert decision.reason == "least_open_workload_then_full_name_then_id"
    assert decision.eligible_count == 1
    assert decision.excluded_inactive_count == 1
    assert decision.excluded_on_leave_count == 0


def test_resolve_instructor_excludes_user_on_active_leave(db_session, users, departments) -> None:
    now = datetime.now(timezone.utc)
    _add_leave(db_session, users, users["staff2"], now - timedelta(hours=1), now + timedelta(hours=1))

    decision = _resolve_instructor(
        db_session, department_id=departments["registry"].id, at=now
    )

    assert decision.instructor is not None
    assert decision.instructor.id == users["staff"].id
    assert decision.excluded_on_leave_count == 1


def test_resolve_instructor_leave_end_boundary_is_exclusive(db_session, users, departments) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    _add_leave(db_session, users, users["staff"], now - timedelta(hours=1), now)
    _add_leave(db_session, users, users["staff2"], now - timedelta(hours=2), now)

    decision = _resolve_instructor(
        db_session, department_id=departments["registry"].id, at=now
    )

    assert decision.instructor is not None
    assert decision.instructor.id == users["staff2"].id
    assert decision.excluded_on_leave_count == 0


def test_resolve_instructor_excludes_inactive_staff(db_session, users, departments) -> None:
    users["staff2"].is_active = False
    db_session.commit()

    decision = _resolve_instructor(db_session, department_id=departments["registry"].id)

    assert decision.instructor is not None
    assert decision.instructor.id == users["staff"].id
    assert decision.excluded_inactive_count == 1


def test_resolve_instructor_excludes_hod_and_admin(db_session, users, departments) -> None:
    decision = _resolve_instructor(db_session, department_id=departments["other"].id)

    assert decision.instructor is None
    assert decision.reason == "no_eligible_instructor"
    assert decision.eligible_count == 0


def test_resolve_instructor_prefers_lowest_open_workload(db_session, users, departments) -> None:
    # staff2 sorts first by name; one open assignment must make staff win.
    _add_assigned_ticket(db_session, users, departments, users["staff2"], status="in_progress")

    decision = _resolve_instructor(db_session, department_id=departments["registry"].id)

    assert decision.instructor is not None
    assert decision.instructor.id == users["staff"].id


def test_resolve_instructor_uses_lowercase_full_name_then_id_tie_break(
    db_session, users, departments
) -> None:
    # Fixture staff: "Alan Staff" (staff2, lower name) and "Grace Staff".
    decision = _resolve_instructor(db_session, department_id=departments["registry"].id)
    assert decision.instructor is not None
    assert decision.instructor.id == users["staff2"].id

    users["staff"].is_active = False
    users["staff2"].is_active = False
    first = _add_staff(
        db_session,
        departments,
        email="same.a@university.edu",
        full_name="Same Name",
    )
    second = _add_staff(
        db_session,
        departments,
        email="same.b@university.edu",
        full_name="Same Name",
    )

    decision = _resolve_instructor(db_session, department_id=departments["registry"].id)
    assert decision.instructor is not None
    assert decision.instructor.id == min(first.id, second.id)


# --- Integration tests for assignment side effects --------------------------


def test_auto_routing_assigns_instructor_with_history_audit_and_single_notification(
    client, db_session, users, departments
) -> None:
    response = _submit_auto(client, users, departments)
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["auto_routed"] is True
    assert body["department_id"] == departments["registry"].id
    assert body["assigned_to"] == users["staff2"].id
    assert body["status"] == "assigned"

    ticket_id = body["id"]
    assignment = db_session.scalar(
        select(TicketAssignmentHistory).where(
            TicketAssignmentHistory.ticket_id == ticket_id,
            TicketAssignmentHistory.from_assignee_id.is_(None),
            TicketAssignmentHistory.to_assignee_id == users["staff2"].id,
        )
    )
    assert assignment is not None
    assert assignment.changed_by_id is None

    status_rows = db_session.scalars(
        select(TicketStatusHistory)
        .where(TicketStatusHistory.ticket_id == ticket_id)
        .order_by(TicketStatusHistory.id)
    ).all()
    assert [(row.from_status, row.to_status) for row in status_rows] == [
        (None, "new"),
        ("new", "assigned"),
    ]
    assert status_rows[1].changed_by_id is None

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == str(ticket_id),
            AuditLog.action == "ticket.instructor_auto_assigned",
        )
    )
    assert audit is not None
    assert audit.actor_id is None
    assert audit.actor_role == "system"
    assert audit.is_override is False
    assert audit.details["assignee_id"] == users["staff2"].id

    assigned_rows = _notification_rows(
        db_session,
        ticket_id=ticket_id,
        recipient_id=users["staff2"].id,
        event_type=TICKET_ASSIGNED,
    )
    assert len(assigned_rows) == 1
    assert not _notification_rows(
        db_session,
        ticket_id=ticket_id,
        recipient_id=users["staff2"].id,
        event_type=TICKET_CREATED,
    )

    # Department/HOD/admin notifications are preserved for the other recipients.
    hod_rows = _notification_rows(
        db_session,
        ticket_id=ticket_id,
        recipient_id=users["hod"].id,
        event_type=TICKET_CREATED,
    )
    admin_rows = _notification_rows(
        db_session,
        ticket_id=ticket_id,
        recipient_id=users["admin"].id,
        event_type=TICKET_CREATED,
    )
    assert len(hod_rows) == 1
    assert len(admin_rows) == 1


def test_no_eligible_instructor_leaves_ticket_new_and_audits_skip(
    client, db_session, users, departments
) -> None:
    response = client.post(
        BASE,
        json={
            "subject": "Scholarships award deadline",
            "description": "Please confirm the scholarships award rules for this term.",
            "department_id": None,
            "auto_route": True,
        },
        headers=auth_header(client, users["student"].email),
    )
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["auto_routed"] is True
    assert body["department_id"] == departments["scholarships"].id
    assert body["assigned_to"] is None
    assert body["status"] == "new"

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == str(body["id"]),
            AuditLog.action == "ticket.instructor_routing_skipped",
        )
    )
    assert audit is not None
    assert audit.actor_role == "system"
    assert audit.details["reason"] == "no_eligible_instructor"
    assert "excluded_on_leave_count" in audit.details
    assert "excluded_inactive_count" in audit.details

    admin_rows = _notification_rows(
        db_session,
        ticket_id=body["id"],
        recipient_id=users["admin"].id,
        event_type=TICKET_CREATED,
    )
    assert len(admin_rows) == 1
    assert not db_session.scalar(
        select(TicketAssignmentHistory).where(TicketAssignmentHistory.ticket_id == body["id"])
    )


def test_manual_assignment_overrides_auto_assignment(client, db_session, users, departments) -> None:
    ticket = _submit_auto(client, users, departments).json()

    response = client.post(
        f"{BASE}/{ticket['id']}/assign",
        json={"assignee_id": users["staff"].id},
        headers=auth_header(client, users["hod"].email),
    )
    assert response.status_code == 200, response.text
    assert response.json()["ticket"]["assigned_to"] == users["staff"].id

    rows = db_session.scalars(
        select(TicketAssignmentHistory)
        .where(TicketAssignmentHistory.ticket_id == ticket["id"])
        .order_by(TicketAssignmentHistory.id)
    ).all()
    assert [(row.from_assignee_id, row.to_assignee_id) for row in rows] == [
        (None, users["staff2"].id),
        (users["staff2"].id, users["staff"].id),
    ]
    assert rows[1].changed_by_id == users["hod"].id


def test_unauthorized_assignment_rejection(client, users, departments) -> None:
    ticket = _submit_auto(client, users, departments).json()

    for email in (users["student"].email, users["staff"].email):
        response = client.post(
            f"{BASE}/{ticket['id']}/assign",
            json={"assignee_id": users["staff"].id},
            headers=auth_header(client, email),
        )
        assert response.status_code == 403


def test_explicit_department_without_auto_route_does_not_auto_assign(
    client, db_session, users, departments
) -> None:
    response = client.post(
        BASE,
        json={
            "subject": "Registry records correction request",
            "description": "Please correct the student records entry for this term.",
            "department_id": departments["registry"].id,
            "auto_route": False,
        },
        headers=auth_header(client, users["student"].email),
    )
    assert response.status_code == 201, response.text

    body = response.json()
    assert body["auto_routed"] is False
    assert body["assigned_to"] is None
    assert body["status"] == "new"
    assert not db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == str(body["id"]),
            AuditLog.action.in_(
                ("ticket.instructor_auto_assigned", "ticket.instructor_routing_skipped")
            ),
        )
    )


def test_manual_assignment_to_instructor_on_leave_preserves_auto_reply(
    client, db_session, users, departments
) -> None:
    now = datetime.now(timezone.utc)
    _add_leave(db_session, users, users["staff"], now - timedelta(hours=1), now + timedelta(hours=1))
    ticket = client.post(
        BASE,
        json={
            "subject": "Registry records correction request",
            "description": "Please correct the student records entry for this term.",
            "department_id": departments["registry"].id,
            "auto_route": False,
        },
        headers=auth_header(client, users["student"].email),
    ).json()
    assert ticket["assigned_to"] is None

    response = client.post(
        f"{BASE}/{ticket['id']}/assign",
        json={"assignee_id": users["staff"].id},
        headers=auth_header(client, users["admin"].email),
    )
    assert response.status_code == 200, response.text

    message = db_session.scalar(
        select(Message).where(
            Message.ticket_id == ticket["id"],
            Message.sender_id == users["staff"].id,
            Message.is_internal.is_(False),
        )
    )
    assert message is not None
    assert message.message_body == "I am on leave; another instructor will respond."

    reply_rows = _notification_rows(
        db_session,
        ticket_id=ticket["id"],
        recipient_id=users["student"].id,
        event_type=AUTO_REPLY,
    )
    assert len(reply_rows) == 1


# --- Intake adapter routing --------------------------------------------------


def test_email_inbound_auto_route_assigns_instructor(
    monkeypatch, client, db_session, users, departments
) -> None:
    monkeypatch.setattr(settings, "INTAKE_WEBHOOK_TOKEN", "valid-intake-token")
    response = client.post(
        EMAIL_URL,
        json={
            "student_email": users["student"].email,
            "subject": "Registry records correction request",
            "body": "Please correct the student records entry for this term.",
            "from_email": "student@example.invalid",
            "department_id": None,
            "auto_route": True,
        },
        headers={"X-Intake-Token": "valid-intake-token"},
    )
    assert response.status_code == 200, response.text

    ticket = response.json()["ticket"]
    assert ticket["channel"] == "email"
    assert ticket["department_id"] == departments["registry"].id
    assert ticket["assigned_to"] == users["staff2"].id
    assert ticket["status"] == "assigned"


def test_whatsapp_inbound_auto_route_assigns_instructor(
    monkeypatch, client, db_session, users, departments
) -> None:
    monkeypatch.setattr(settings, "INTAKE_WEBHOOK_TOKEN", "valid-intake-token")
    response = client.post(
        WHATSAPP_URL,
        json={
            "student_email": users["student"].email,
            "body": "Please correct the registry student records entry for this term.",
            "from_phone": "+15550001111",
            "department_id": None,
            "auto_route": True,
        },
        headers={"X-Intake-Token": "valid-intake-token"},
    )
    assert response.status_code == 200, response.text

    ticket = response.json()["ticket"]
    assert ticket["channel"] == "whatsapp"
    assert ticket["department_id"] == departments["registry"].id
    assert ticket["assigned_to"] == users["staff2"].id
    assert ticket["status"] == "assigned"
