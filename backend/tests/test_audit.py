"""Admin-only audit reader with real AuditLog rows and filters."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.api.routes.audit import router as audit_router
from app.core.config import settings
from app.main import app
from app.models import AuditLog
from tests.conftest import TEST_PASSWORD, auth_header

BASE = "/api/v1/audit"

if not any(getattr(route, "path", None) == f"{settings.API_V1_PREFIX}/audit" for route in app.routes):
    app.include_router(audit_router, prefix=settings.API_V1_PREFIX)


def submit(client, users, departments):
    return client.post(
        "/api/v1/tickets",
        json={
            "subject": "Audit visible ticket",
            "description": "A ticket whose creation should be audited",
            "department_id": departments["registry"].id,
        },
        headers=auth_header(client, users["student"].email),
    )


def test_audit_is_admin_only(client, users) -> None:
    assert client.get(BASE).status_code == 401
    for role in ("student", "staff", "hod"):
        response = client.get(BASE, headers=auth_header(client, users[role].email))
        assert response.status_code == 403, role
    assert client.get(BASE, headers=auth_header(client, users["admin"].email)).status_code == 200


def test_audit_returns_real_rows_with_actor_email(client, db_session, users, departments) -> None:
    created = submit(client, users, departments)
    assert created.status_code == 201, created.text
    ticket_id = created.json()["id"]

    response = client.get(BASE, headers=auth_header(client, users["admin"].email))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True and body["total"] >= 1
    row = next(item for item in body["items"] if item["action"] == "ticket.created")
    assert row["entity_type"] == "ticket"
    assert row["entity_id"] == str(ticket_id)
    assert row["actor_id"] == users["student"].id
    assert row["actor_email"] == users["student"].email
    assert row["is_override"] is False
    assert "created_at" in row

    stored = db_session.get(AuditLog, row["id"])
    assert stored is not None
    assert stored.action == "ticket.created"


def test_audit_filters_and_pagination(client, users, departments) -> None:
    ticket = submit(client, users, departments).json()
    admin = auth_header(client, users["admin"].email)

    by_action = client.get(BASE, params={"action": "ticket.created"}, headers=admin).json()
    assert by_action["total"] == 1
    assert by_action["items"][0]["action"] == "ticket.created"

    by_actor = client.get(
        BASE, params={"actor_id": users["student"].id, "action": "ticket.created"}, headers=admin
    ).json()
    assert by_actor["total"] == 1

    wrong_actor = client.get(
        BASE, params={"actor_id": users["admin"].id, "action": "ticket.created"}, headers=admin
    ).json()
    assert wrong_actor["total"] == 0

    by_entity = client.get(
        BASE,
        params={"entity_type": "ticket", "entity_id": ticket["id"], "action": "ticket.created"},
        headers=admin,
    ).json()
    assert by_entity["total"] == 1

    now = datetime.now(timezone.utc)
    after = client.get(
        BASE,
        params={"from": (now - timedelta(days=1)).isoformat(), "action": "ticket.created"},
        headers=admin,
    ).json()
    before = client.get(
        BASE,
        params={"to": (now - timedelta(days=1)).isoformat(), "action": "ticket.created"},
        headers=admin,
    ).json()
    assert after["total"] == 1
    assert before["total"] == 0

    paged = client.get(BASE, params={"skip": 0, "limit": 1}, headers=admin).json()
    assert paged["limit"] == 1 and len(paged["items"]) == 1
    assert client.get(BASE, params={"limit": 501}, headers=admin).status_code == 422


def test_no_synthetic_auth_audit_endpoint(client, db_session, users, departments) -> None:
    submit(client, users, departments)
    assert client.post(
        BASE + "/auth", json={"email": users["admin"].email}, headers=auth_header(client, users["admin"].email)
    ).status_code == 404
