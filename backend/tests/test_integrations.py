"""Inbound webhook security and integration status flag tests."""

from __future__ import annotations

from app.core.config import settings
from app.models import Ticket
from tests.conftest import auth_header

STATUS_URL = "/api/v1/integrations/status"
EMAIL_URL = "/api/v1/integrations/email/inbound"
WHATSAPP_URL = "/api/v1/integrations/whatsapp/inbound"
VERIFY_URL = "/api/v1/integrations/whatsapp/webhook"


def _email_body(users, departments, **overrides):
    body = {
        "student_email": users["student"].email,
        "subject": "Inbound email subject",
        "body": "This is the body of the inbound email from the student.",
        "from_email": "spoofed@example.invalid",
        "department_id": departments["registry"].id,
        "auto_route": False,
    }
    body.update(overrides)
    return body


def test_status_returns_booleans_only_and_no_secrets(monkeypatch, client) -> None:
    monkeypatch.setattr(settings, "INTAKE_WEBHOOK_TOKEN", "super-secret-token")
    monkeypatch.setattr(settings, "WHATSAPP_ACCESS_TOKEN", "another-secret-token")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "smtp-secret")
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_ENABLED", True)
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "oauth-client-id")

    response = client.get(STATUS_URL)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "success", "smtp", "whatsapp", "google_oauth", "intake_webhook"
    }
    assert all(isinstance(value, bool) for value in body.values())
    assert "super-secret-token" not in response.text
    assert "another-secret-token" not in response.text
    assert "smtp-secret" not in response.text
    assert "oauth-client-id" not in response.text


def test_inbound_rejects_bad_or_missing_token(monkeypatch, client, users, departments) -> None:
    monkeypatch.setattr(settings, "INTAKE_WEBHOOK_TOKEN", "valid-intake-token")
    body = _email_body(users, departments)

    for headers in ({}, {"X-Intake-Token": "wrong"}):
        response = client.post(EMAIL_URL, json=body, headers=headers)
        assert response.status_code == 401
        assert response.json()["code"] == "invalid_intake_token"


def test_inbound_fails_closed_when_token_unconfigured(monkeypatch, client, users, departments) -> None:
    monkeypatch.setattr(settings, "INTAKE_WEBHOOK_TOKEN", "")
    response = client.post(
        EMAIL_URL,
        json=_email_body(users, departments),
        headers={"X-Intake-Token": "anything"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_intake_token"


def test_email_inbound_creates_ticket_for_existing_mapped_student(
    monkeypatch, client, db_session, users, departments
) -> None:
    monkeypatch.setattr(settings, "INTAKE_WEBHOOK_TOKEN", "valid-intake-token")
    response = client.post(
        EMAIL_URL,
        json=_email_body(users, departments),
        headers={"X-Intake-Token": "valid-intake-token"},
    )
    assert response.status_code == 200, response.text
    ticket = db_session.get(Ticket, response.json()["ticket"]["id"])
    assert ticket is not None
    assert ticket.student_id == users["student"].id
    assert ticket.channel == "email"
    assert ticket.department_id == departments["registry"].id


def test_whatsapp_inbound_creates_ticket_with_whatsapp_channel(
    monkeypatch, client, db_session, users, departments
) -> None:
    monkeypatch.setattr(settings, "INTAKE_WEBHOOK_TOKEN", "valid-intake-token")
    response = client.post(
        WHATSAPP_URL,
        json={
            "student_email": users["student"].email,
            "body": "Please help me reset my university portal password.",
            "from_phone": "+15550001111",
            "department_id": departments["registry"].id,
            "auto_route": False,
        },
        headers={"X-Intake-Token": "valid-intake-token"},
    )
    assert response.status_code == 200, response.text
    ticket = db_session.get(Ticket, response.json()["ticket"]["id"])
    assert ticket is not None
    assert ticket.channel == "whatsapp"
    assert ticket.student_id == users["student"].id


def test_inbound_unknown_student_returns_404(monkeypatch, client, users, departments) -> None:
    monkeypatch.setattr(settings, "INTAKE_WEBHOOK_TOKEN", "valid-intake-token")
    response = client.post(
        EMAIL_URL,
        json=_email_body(users, departments, student_email="unknown@university.edu"),
        headers={"X-Intake-Token": "valid-intake-token"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_inbound_ticket_can_auto_route(monkeypatch, client, db_session, users, departments) -> None:
    monkeypatch.setattr(settings, "INTAKE_WEBHOOK_TOKEN", "valid-intake-token")
    response = client.post(
        EMAIL_URL,
        json=_email_body(
            users,
            departments,
            subject="Scholarships application deadline",
            body="Could you confirm the scholarships award deadline for this term?",
            department_id=None,
            auto_route=True,
        ),
        headers={"X-Intake-Token": "valid-intake-token"},
    )
    assert response.status_code == 200, response.text
    ticket = db_session.get(Ticket, response.json()["ticket"]["id"])
    assert ticket.auto_routed is True
    assert ticket.department_id == departments["scholarships"].id


def test_whatsapp_verify_handshake_returns_challenge(monkeypatch, client) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "meta-verify-token")
    response = client.get(
        VERIFY_URL,
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "challenge-123",
            "hub.verify_token": "meta-verify-token",
        },
    )
    assert response.status_code == 200
    assert response.text == "challenge-123"


def test_whatsapp_verify_fails_closed_for_bad_or_missing_token(monkeypatch, client) -> None:
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "meta-verify-token")
    bad = client.get(
        VERIFY_URL,
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "challenge-123",
            "hub.verify_token": "wrong",
        },
    )
    assert bad.status_code == 401
    assert bad.json()["code"] == "invalid_verify_token"

    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "")
    unconfigured = client.get(
        VERIFY_URL,
        params={
            "hub.mode": "subscribe",
            "hub.challenge": "challenge-123",
            "hub.verify_token": "meta-verify-token",
        },
    )
    assert unconfigured.status_code == 401
