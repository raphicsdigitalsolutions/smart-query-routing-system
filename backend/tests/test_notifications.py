"""Deterministic notification tests: no real SMTP or WhatsApp network calls."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.message import Message as EmailMessage

import pytest
from sqlalchemy import select

from app.models import AuditLog, InstructorLeave, Notification, Ticket, TicketAiAnalysis
from app.schemas.ticket import TicketCreate
from app.services import email as email_service
from app.services import notifications as notification_service
from app.services import whatsapp as whatsapp_service
from app.services.tickets import create_ticket
from tests.conftest import auth_header

BASE = "/api/v1/tickets"


class FakeSMTP:
    sent: list[EmailMessage] = []
    instances: list["FakeSMTP"] = []
    fail = False

    @classmethod
    def reset(cls) -> None:
        cls.sent = []
        cls.instances = []
        cls.fail = False

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        self.logged_in = False
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        self.started_tls = True

    def login(self, user, password):
        self.logged_in = True

    def send_message(self, message):
        if FakeSMTP.fail:
            raise RuntimeError("simulated SMTP outage")
        FakeSMTP.sent.append(message)

    def quit(self):
        return None


@pytest.fixture()
def email_enabled(monkeypatch):
    """Point the email transport at a fake SMTP implementation."""
    FakeSMTP.reset()
    monkeypatch.setattr(email_service.settings, "EMAIL_NOTIFICATIONS_ENABLED", True)
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "smtp.test.local")
    monkeypatch.setattr(email_service.settings, "SMTP_USER", "")
    monkeypatch.setattr(email_service.settings, "SMTP_PASSWORD", "")
    monkeypatch.setattr(email_service.settings, "SMTP_USE_SSL", False)
    monkeypatch.setattr(email_service.settings, "SMTP_USE_TLS", True)
    monkeypatch.setattr(email_service.settings, "SMTP_ATTEMPTS", 2)
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(email_service.smtplib, "SMTP_SSL", FakeSMTP)
    return FakeSMTP


def _submit(client, users, departments, **overrides):
    payload = {
        "subject": "Scholarship deadline clarification",
        "description": "Could you please confirm the current request status?",
        "department_id": departments["registry"].id,
    }
    payload.update(overrides)
    return client.post(BASE, json=payload, headers=auth_header(client, users["student"].email))


def test_new_ticket_notifies_staff_hod_and_admin_by_email_and_in_app(
    client, db_session, users, departments, email_enabled
) -> None:
    response = _submit(client, users, departments)
    assert response.status_code == 201, response.text
    ticket = db_session.get(Ticket, response.json()["id"])
    subject = f"New ticket {ticket.public_reference}"

    email_rows = db_session.scalars(
        select(Notification).where(
            Notification.ticket_id == ticket.id, Notification.channel == "email"
        )
    ).all()
    assert {row.recipient_user_id for row in email_rows} == {
        users["staff"].id,
        users["staff2"].id,
        users["hod"].id,
        users["admin"].id,
    }
    assert all(row.subject == subject for row in email_rows)
    assert all(row.status == "sent" and row.sent_at is not None for row in email_rows)
    assert email_enabled.sent and all(subject in message["Subject"] for message in email_enabled.sent)

    in_app_rows = db_session.scalars(
        select(Notification).where(
            Notification.ticket_id == ticket.id, Notification.channel == "in_app"
        )
    ).all()
    assert len(in_app_rows) == 4
    assert all(row.status == "sent" for row in in_app_rows)


def test_internal_notes_create_no_notifications_and_never_reach_students(
    client, db_session, users, departments, email_enabled
) -> None:
    ticket = _submit(client, users, departments).json()
    assert client.post(
        f"{BASE}/{ticket['id']}/assign",
        json={"assignee_id": users["staff"].id},
        headers=auth_header(client, users["hod"].email),
    ).status_code == 200

    staff_header = auth_header(client, users["staff"].email)
    public = client.post(
        f"{BASE}/{ticket['id']}/messages",
        json={"message_body": "Please upload your transcript.", "is_internal": False},
        headers=staff_header,
    )
    internal = client.post(
        f"{BASE}/{ticket['id']}/messages",
        json={"message_body": "Student is eligible; prioritize internally.", "is_internal": True},
        headers=staff_header,
    )
    assert public.status_code == 201 and internal.status_code == 201

    rows = db_session.scalars(
        select(Notification).where(Notification.ticket_id == ticket["id"])
    ).all()
    assert not any("prioritize internally" in row.body for row in rows)
    outward = [row for row in rows if row.channel in {"email", "whatsapp"}]
    assert all("prioritize internally" not in row.body for row in outward)

    student_messages = client.get(
        f"{BASE}/{ticket['id']}/messages",
        headers=auth_header(client, users["student"].email),
    ).json()
    assert student_messages["total"] == 1
    assert "prioritize" not in str(student_messages)


def test_unapproved_ai_draft_is_never_emailed(
    client, db_session, users, departments, email_enabled
) -> None:
    ticket = _submit(client, users, departments).json()
    draft_text = "DRAFT-UNAPPROVED: confidential suggestion that must not be sent"
    db_session.add(
        TicketAiAnalysis(
            ticket_id=ticket["id"],
            requested_by_id=users["staff"].id,
            version=1,
            status="completed",
            is_current=True,
            classification_json={},
            draft_json={"body": draft_text},
            validation_json={"passed": True, "issues": [], "overall_confidence": 0.9},
            no_evidence=False,
            knowledge_sources_json=[],
            execution_metadata_json=[],
        )
    )
    db_session.commit()

    rows = db_session.scalars(
        select(Notification).where(Notification.ticket_id == ticket["id"])
    ).all()
    assert rows
    assert all(draft_text not in row.body for row in rows)
    assert all(draft_text not in str(message) for message in email_enabled.sent)


def test_smtp_failure_is_recorded_without_failing_ticket_mutation(
    client, db_session, users, departments, email_enabled
) -> None:
    email_enabled.fail = True
    response = _submit(client, users, departments)
    assert response.status_code == 201, response.text
    assert db_session.get(Ticket, response.json()["id"]) is not None

    failed = db_session.scalars(
        select(Notification).where(
            Notification.ticket_id == response.json()["id"],
            Notification.channel == "email",
            Notification.status == "failed",
        )
    ).all()
    assert len(failed) == 4
    assert all(row.attempts == 2 for row in failed)
    assert all(row.last_error and "simulated SMTP outage" not in row.last_error for row in failed)
    assert all("RuntimeError" in row.last_error for row in failed)
    assert all(row.sent_at is None for row in failed)


def test_email_rows_are_idempotent_within_short_window(
    db_session, users, departments, email_enabled
) -> None:
    ticket = create_ticket(
        db_session,
        TicketCreate(
            subject="Idempotency check request",
            description="This description is long enough for validation.",
            department_id=departments["registry"].id,
        ),
        users["student"],
    )
    ticket_row = db_session.get(Ticket, ticket.id)
    for _ in range(2):
        notification_service.notify_ticket_event(
            db_session,
            ticket=ticket_row,
            event_type=notification_service.PUBLIC_REPLY,
            recipients=[users["staff"]],
            subject="Duplicate check",
            public_message="A public reply body.",
        )
    db_session.commit()

    rows = db_session.scalars(
        select(Notification).where(
            Notification.ticket_id == ticket.id,
            Notification.event_type == notification_service.PUBLIC_REPLY,
            Notification.channel == "email",
        )
    ).all()
    assert len(rows) == 1


def test_notifications_are_owner_only(client, db_session, users, departments, email_enabled) -> None:
    ticket = _submit(client, users, departments).json()
    rows = db_session.scalars(
        select(Notification).where(
            Notification.ticket_id == ticket["id"],
            Notification.channel == "in_app",
            Notification.recipient_user_id == users["staff"].id,
        )
    ).all()
    assert rows

    staff_header = auth_header(client, users["staff"].email)
    listing = client.get("/api/v1/notifications", headers=staff_header)
    assert listing.status_code == 200, listing.text
    assert any(item["id"] == rows[0].id for item in listing.json()["items"])

    marked = client.post(f"/api/v1/notifications/{rows[0].id}/read", headers=staff_header)
    assert marked.status_code == 200, marked.text
    assert marked.json()["notification"]["read_at"] is not None

    student_header = auth_header(client, users["student"].email)
    assert client.get(f"/api/v1/notifications?limit=100", headers=student_header).status_code == 200
    denied = client.post(f"/api/v1/notifications/{rows[0].id}/read", headers=student_header)
    assert denied.status_code == 404
    assert denied.json()["code"] == "not_found"


def test_assignment_auto_reply_is_public_audited_and_notifies_student(
    client, db_session, users, departments, email_enabled
) -> None:
    ticket = _submit(client, users, departments).json()
    now = datetime.now(timezone.utc)
    db_session.add(
        InstructorLeave(
            user_id=users["staff"].id,
            start_at=now - timedelta(days=1),
            end_at=now + timedelta(days=1),
            reason="Annual leave",
            auto_reply="I am on leave until Monday; another colleague will respond.",
            is_active=True,
            created_by_id=users["admin"].id,
        )
    )
    db_session.commit()

    assigned = client.post(
        f"{BASE}/{ticket['id']}/assign",
        json={"assignee_id": users["staff"].id},
        headers=auth_header(client, users["admin"].email),
    )
    assert assigned.status_code == 200, assigned.text

    messages = client.get(
        f"{BASE}/{ticket['id']}/messages",
        headers=auth_header(client, users["student"].email),
    ).json()
    assert any(
        "I am on leave until Monday" in item["message_body"] and item["is_internal"] is False
        for item in messages["items"]
    )

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.action == "message.created",
            AuditLog.entity_id == str(ticket["id"]),
        )
    )
    assert audit is not None and audit.details.get("auto_reply") is True

    rows = db_session.scalars(
        select(Notification).where(
            Notification.ticket_id == ticket["id"],
            Notification.event_type == notification_service.AUTO_REPLY,
            Notification.recipient_user_id == users["student"].id,
        )
    ).all()
    assert rows


def test_whatsapp_delivery_failure_is_recorded_not_raised(
    db_session, users, departments, monkeypatch, email_enabled
) -> None:
    class FailedResponse:
        def raise_for_status(self):
            raise RuntimeError("provider down token=FAKE-SECRET-MARKER-DO-NOT-LOG")

        def json(self):
            return {}

    monkeypatch.setattr(whatsapp_service.settings, "WHATSAPP_ENABLED", True)
    monkeypatch.setattr(whatsapp_service.settings, "WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setattr(whatsapp_service.settings, "WHATSAPP_PHONE_NUMBER_ID", "123")
    monkeypatch.setattr(whatsapp_service.httpx, "post", lambda *a, **k: FailedResponse())

    ticket = create_ticket(
        db_session,
        TicketCreate(
            subject="WhatsApp outbound check",
            description="This description is long enough for validation.",
            department_id=departments["registry"].id,
            channel="whatsapp",
        ),
        users["student"],
    )
    rows = notification_service.notify_ticket_event(
        db_session,
        ticket=db_session.get(Ticket, ticket.id),
        event_type=notification_service.PUBLIC_REPLY,
        recipients=[users["student"]],
        subject="WhatsApp test",
        public_message="A public reply.",
        address_overrides={users["student"].id: "+15550000000"},
    )
    db_session.commit()
    whatsapp_rows = [row for row in rows if row.channel == "whatsapp"]
    assert len(whatsapp_rows) == 1
    assert whatsapp_rows[0].status == "failed"
    assert whatsapp_rows[0].last_error
    assert "FAKE-SECRET-MARKER-DO-NOT-LOG" not in whatsapp_rows[0].last_error
    assert "provider down" not in whatsapp_rows[0].last_error
    assert "RuntimeError" in whatsapp_rows[0].last_error
