"""Announcement CRUD, audience visibility, publishing and audits."""

from sqlalchemy import select

from app.api.routes.announcements import router as announcements_router
from app.core.config import settings
from app.main import app
from app.models import Announcement, AuditLog
from tests.conftest import auth_header

BASE = "/api/v1/announcements"

if not any(getattr(route, "path", None) == f"{settings.API_V1_PREFIX}/announcements" for route in app.routes):
    app.include_router(announcements_router, prefix=settings.API_V1_PREFIX)


def create(client, admin_headers, **overrides):
    payload = {
        "title": "Scheduled maintenance",
        "body": "The portal will be unavailable on Sunday.",
        "audience_roles": ["student"],
    }
    payload.update(overrides)
    return client.post(BASE, json=payload, headers=admin_headers)


def test_audience_visibility_by_role_and_department(client, users, departments) -> None:
    admin = auth_header(client, users["admin"].email)
    student_only = create(client, admin).json()
    scoped = create(
        client,
        admin,
        title="Registry staff note",
        body="Please complete the new training.",
        audience_roles=["staff", "hod"],
        department_id=departments["registry"].id,
    ).json()
    assert student_only["published_at"] is not None
    assert scoped["department_id"] == departments["registry"].id

    def ids(email: str):
        response = client.get(BASE, headers=auth_header(client, email))
        assert response.status_code == 200, response.text
        return {item["id"] for item in response.json()["items"]}

    assert ids(users["student"].email) == {student_only["id"]}
    assert ids(users["staff"].email) == {scoped["id"]}
    assert ids(users["hod"].email) == {scoped["id"]}
    assert ids(users["hod_other"].email) == set()
    assert ids(users["admin"].email) == set()  # admin is not in either audience


def test_inactive_announcement_and_publish_timestamp(client, db_session, users) -> None:
    admin = auth_header(client, users["admin"].email)
    created = create(client, admin, is_active=False, audience_roles=["admin"]).json()
    assert created["published_at"] is None
    assert client.get(BASE, headers=admin).json()["total"] == 0

    activated = client.patch(
        f"{BASE}/{created['id']}", json={"is_active": True}, headers=admin
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["published_at"] is not None
    assert client.get(BASE, headers=admin).json()["total"] == 1
    assert db_session.get(Announcement, created["id"]).published_at is not None


def test_role_validation(client, users) -> None:
    admin = auth_header(client, users["admin"].email)
    invalid = create(client, admin, audience_roles=["student", "superuser"])
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "validation_error"
    empty = create(client, admin, audience_roles=[])
    assert empty.status_code == 422
    invalid_patch = client.patch(
        f"{BASE}/1", json={"audience_roles": ["nope"]}, headers=admin
    )
    assert invalid_patch.status_code == 422


def test_admin_only_mutations_and_audits(client, db_session, users) -> None:
    admin = auth_header(client, users["admin"].email)
    created = create(client, admin, audience_roles=["staff"]).json()
    audit = db_session.scalars(
        select(AuditLog).where(AuditLog.action == "announcement.created")
    ).one()
    assert audit.actor_id == users["admin"].id
    assert audit.entity_id == str(created["id"])

    staff = auth_header(client, users["staff"].email)
    assert client.post(BASE, json={
        "title": "Nope", "body": "Nope body", "audience_roles": ["staff"]
    }, headers=staff).status_code == 403
    assert client.patch(f"{BASE}/{created['id']}", json={"title": "Nope"}, headers=staff).status_code == 403
    assert client.delete(f"{BASE}/{created['id']}", headers=staff).status_code == 403

    updated = client.patch(
        f"{BASE}/{created['id']}", json={"body": "Updated body text"}, headers=admin
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["body"] == "Updated body text"

    deactivated = client.patch(
        f"{BASE}/{created['id']}", json={"is_active": False}, headers=admin
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["published_at"] is not None
    actions = {
        row.action
        for row in db_session.scalars(select(AuditLog)).all()
        if row.entity_type == "announcement"
    }
    assert {"announcement.created", "announcement.updated", "announcement.deactivated"} <= actions


def test_delete_deactivates_and_hides(client, db_session, users) -> None:
    admin = auth_header(client, users["admin"].email)
    created = create(client, admin, audience_roles=["student"]).json()
    student = auth_header(client, users["student"].email)
    assert client.get(BASE, headers=student).json()["total"] == 1

    deleted = client.delete(f"{BASE}/{created['id']}", headers=admin)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["is_active"] is False
    assert client.get(BASE, headers=student).json()["total"] == 0
    assert client.delete(f"{BASE}/9999", headers=admin).status_code == 404
