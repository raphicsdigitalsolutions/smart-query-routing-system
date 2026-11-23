"""Serverless-compatible escalation trigger protected by a shared secret."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.core.config import settings
from app.models import AuditLog, Ticket
from tests.conftest import auth_header

BASE = "/api/v1/tickets"
SECRET = "test-cron-secret-1234567890"


def _make_old_ticket(client, db_session, users, departments, *, hours_old=30):
    response = client.post(
        BASE,
        json={
            "subject": "Serverless escalation candidate",
            "description": "This request is old enough to be escalated by a cron trigger.",
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


def test_cron_escalation_requires_configured_secret(client, db_session, users, departments, monkeypatch) -> None:
    ticket_id = _make_old_ticket(client, db_session, users, departments)
    monkeypatch.setattr(settings, "ESCALATION_CRON_SECRET", "")

    missing = client.post(f"{BASE}/escalation/sweep", headers={"X-Cron-Secret": SECRET})
    assert missing.status_code == 503
    assert missing.json()["code"] == "escalation_cron_not_configured"
    assert db_session.get(Ticket, ticket_id).is_escalated is False


def test_cron_escalation_rejects_invalid_secret(client, db_session, users, departments, monkeypatch) -> None:
    ticket_id = _make_old_ticket(client, db_session, users, departments)
    monkeypatch.setattr(settings, "ESCALATION_CRON_SECRET", SECRET)

    denied = client.post(f"{BASE}/escalation/sweep", headers={"X-Cron-Secret": "wrong-secret"})
    assert denied.status_code == 401
    assert denied.json()["code"] == "invalid_cron_secret"
    assert db_session.get(Ticket, ticket_id).is_escalated is False


def test_cron_escalation_runs_repeat_safely(client, db_session, users, departments, monkeypatch) -> None:
    ticket_id = _make_old_ticket(client, db_session, users, departments)
    monkeypatch.setattr(settings, "ESCALATION_CRON_SECRET", SECRET)

    first = client.post(f"{BASE}/escalation/sweep", headers={"X-Cron-Secret": SECRET})
    assert first.status_code == 200, first.text
    assert first.json() == {"success": True, "scanned": 1, "escalated": 1}

    second = client.post(f"{BASE}/escalation/sweep", headers={"X-Cron-Secret": SECRET})
    assert second.status_code == 200, second.text
    assert second.json() == {"success": True, "scanned": 0, "escalated": 0}

    ticket = db_session.get(Ticket, ticket_id)
    assert ticket.is_escalated is True
    audit_rows = db_session.scalars(
        select(AuditLog).where(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == str(ticket_id),
            AuditLog.action == "ticket.escalated_automatically",
        )
    ).all()
    assert len(audit_rows) == 1
