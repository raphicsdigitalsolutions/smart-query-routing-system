"""Leave scoping, window validation, auto-reply lookup and audits."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.api.routes.leave import router as leave_router
from app.core.config import settings
from app.main import app
from app.models import AuditLog, InstructorLeave
from app.services.leave import active_auto_reply
from tests.conftest import auth_header

BASE = "/api/v1/leave"

if not any(getattr(route, "path", None) == f"{settings.API_V1_PREFIX}/leave" for route in app.routes):
    app.include_router(leave_router, prefix=settings.API_V1_PREFIX)


def window(hours_before: int = 1, hours_after: int = 1, **overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "start_at": (now - timedelta(hours=hours_before)).isoformat(),
        "end_at": (now + timedelta(hours=hours_after)).isoformat(),
        "auto_reply": "I am on leave; please contact the help desk.",
        "reason": "Conference",
    }
    payload.update(overrides)
    return payload


def create(client, headers, **overrides):
    return client.post(BASE, json=window(**overrides), headers=headers)


def test_staff_creates_own_leave_and_cannot_create_for_others(client, db_session, users) -> None:
    staff = auth_header(client, users["staff"].email)
    response = create(client, staff)
    assert response.status_code == 201, response.text
    body = response.json()["leave"]
    assert body["user_id"] == users["staff"].id
    assert body["user_email"] == users["staff"].email
    assert body["is_active"] is True

    other = create(client, staff, user_id=users["staff2"].id)
    assert other.status_code == 403

    audit = db_session.scalars(select(AuditLog).where(AuditLog.action == "leave.created")).one()
    assert audit.actor_id == users["staff"].id
    assert audit.entity_id == str(body["id"])


def test_hod_and_admin_creation_permissions(client, users) -> None:
    hod = auth_header(client, users["hod"].email)
    within = create(client, hod, user_id=users["staff2"].id)
    assert within.status_code == 201, within.text
    assert within.json()["leave"]["user_id"] == users["staff2"].id

    outside = create(client, hod, user_id=users["hod_other"].id)
    assert outside.status_code == 403

    admin = auth_header(client, users["admin"].email)
    any_user = create(client, admin, user_id=users["hod_other"].id)
    assert any_user.status_code == 201, any_user.text
    assert any_user.json()["leave"]["user_id"] == users["hod_other"].id


def test_invalid_window_is_rejected(client, users) -> None:
    admin = auth_header(client, users["admin"].email)
    now = datetime.now(timezone.utc)
    response = client.post(
        BASE,
        json={
            "start_at": now.isoformat(),
            "end_at": (now - timedelta(hours=1)).isoformat(),
            "auto_reply": "Back soon",
        },
        headers=admin,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_leave_window"

    created = create(client, admin).json()["leave"]
    invalid_patch = client.patch(
        f"{BASE}/{created['id']}",
        json={"end_at": (now - timedelta(days=2)).isoformat()},
        headers=admin,
    )
    assert invalid_patch.status_code == 400
    assert invalid_patch.json()["code"] == "invalid_leave_window"


def test_list_permissions_and_scoping(client, db_session, users) -> None:
    admin = auth_header(client, users["admin"].email)
    mine = create(client, auth_header(client, users["staff"].email)).json()["leave"]
    colleague = create(client, admin, user_id=users["staff2"].id).json()["leave"]
    outside = create(client, admin, user_id=users["hod_other"].id).json()["leave"]

    def ids(headers):
        response = client.get(BASE, headers=headers)
        assert response.status_code == 200, response.text
        return {item["id"] for item in response.json()["items"]}

    assert ids(auth_header(client, users["staff"].email)) == {mine["id"]}
    assert ids(auth_header(client, users["hod"].email)) == {mine["id"], colleague["id"]}
    assert ids(admin) == {mine["id"], colleague["id"], outside["id"]}
    assert client.get(BASE, headers=auth_header(client, users["student"].email)).status_code == 403


def test_active_auto_reply_covers_only_active_intervals(client, db_session, users) -> None:
    staff = users["staff"]
    admin = auth_header(client, users["admin"].email)
    now = datetime.now(timezone.utc)
    first = client.post(
        BASE,
        json={
            "start_at": (now - timedelta(days=3)).isoformat(),
            "end_at": (now - timedelta(days=2)).isoformat(),
            "auto_reply": "Old reply",
            "user_id": staff.id,
        },
        headers=admin,
    ).json()["leave"]
    assert first["user_id"] == staff.id

    client.post(
        BASE,
        json={
            "start_at": (now - timedelta(hours=1)).isoformat(),
            "end_at": (now + timedelta(hours=1)).isoformat(),
            "auto_reply": "Current reply",
        },
        headers=auth_header(client, staff.email),
    )
    client.post(
        BASE,
        json={
            "start_at": (now - timedelta(hours=2)).isoformat(),
            "end_at": (now + timedelta(hours=2)).isoformat(),
            "auto_reply": "Disabled reply",
            "is_active": False,
            "user_id": staff.id,
        },
        headers=admin,
    )

    assert active_auto_reply(db_session, staff.id, at=now) == "Current reply"
    assert active_auto_reply(db_session, staff.id, at=now - timedelta(days=3, seconds=1)) is None
    assert active_auto_reply(db_session, staff.id, at=now - timedelta(days=2) + timedelta(seconds=1)) is None
    assert active_auto_reply(db_session, staff.id, at=now + timedelta(hours=1)) is None
    assert active_auto_reply(db_session, users["student"].id, at=now) is None
    assert active_auto_reply(db_session, staff.id) == "Current reply"


def test_update_delete_permissions_and_deactivation_audit(client, db_session, users) -> None:
    owner = auth_header(client, users["staff"].email)
    created = create(client, owner).json()["leave"]
    other_staff = auth_header(client, users["staff2"].email)
    admin = auth_header(client, users["admin"].email)

    forbidden = client.patch(
        f"{BASE}/{created['id']}", json={"auto_reply": "Hacked"}, headers=other_staff
    )
    assert forbidden.status_code == 403

    updated = client.patch(
        f"{BASE}/{created['id']}", json={"auto_reply": "Updated reply"}, headers=owner
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["leave"]["auto_reply"] == "Updated reply"

    deleted = client.delete(f"{BASE}/{created['id']}", headers=admin)
    assert deleted.status_code == 200
    assert deleted.json()["leave"]["is_active"] is False
    row = db_session.get(InstructorLeave, created["id"])
    assert row is not None and row.is_active is False
    actions = {entry.action for entry in db_session.scalars(select(AuditLog)).all()}
    assert {"leave.created", "leave.updated", "leave.deactivated"} <= actions
