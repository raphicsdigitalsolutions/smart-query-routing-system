"""FR-14b: password authentication events must be auditable."""

from sqlalchemy import select

from app.models import AuditLog
from tests.conftest import TEST_PASSWORD, auth_header

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"


def _latest_action(db_session, action: str) -> AuditLog | None:
    return db_session.scalar(
        select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.id.desc())
    )


def test_register_records_audit_event(client, db_session) -> None:
    response = client.post(
        REGISTER_URL,
        json={
            "full_name": "Audit Student",
            "email": "audit-student@university.edu",
            "password": TEST_PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]

    log = _latest_action(db_session, "auth.registered")
    assert log is not None
    assert log.actor_id == user_id
    assert log.actor_role == "student"
    assert log.entity_type == "user"
    assert log.entity_id == str(user_id)
    assert log.details == {"email": "audit-student@university.edu"}
    assert log.is_override is False


def test_login_records_success_and_failure_audit_events(client, db_session, users) -> None:
    success = client.post(
        LOGIN_URL,
        json={"email": users["student"].email, "password": TEST_PASSWORD},
    )
    assert success.status_code == 200, success.text

    success_log = _latest_action(db_session, "auth.login_succeeded")
    assert success_log is not None
    assert success_log.actor_id == users["student"].id
    assert success_log.actor_role == "student"
    assert success_log.entity_type == "user"
    assert success_log.entity_id == str(users["student"].id)
    assert success_log.details == {"email": users["student"].email}

    failure = client.post(
        LOGIN_URL,
        json={"email": users["student"].email, "password": "wrong-password"},
    )
    assert failure.status_code == 401

    failure_log = _latest_action(db_session, "auth.login_failed")
    assert failure_log is not None
    assert failure_log.actor_id == users["student"].id
    assert failure_log.entity_type == "user"
    assert failure_log.entity_id == str(users["student"].id)
    assert failure_log.details["email"] == users["student"].email
    assert failure_log.details["reason"] == "invalid_credentials"

    unknown = client.post(
        LOGIN_URL,
        json={"email": "missing-user@university.edu", "password": "wrong-password"},
    )
    assert unknown.status_code == 401

    unknown_log = _latest_action(db_session, "auth.login_failed")
    assert unknown_log is not None
    assert unknown_log.actor_id is None
    assert unknown_log.entity_id == "missing-user@university.edu"
    assert unknown_log.details["reason"] == "user_not_found"


def test_authenticated_profile_read_does_not_create_login_audit(client, db_session, users) -> None:
    header = auth_header(client, users["student"].email)
    response = client.get("/api/v1/auth/me", headers=header)
    assert response.status_code == 200

    logs = db_session.scalars(
        select(AuditLog).where(AuditLog.action.in_(["auth.login_succeeded", "auth.registered"]))
    ).all()
    # auth_header login creates one login_succeeded record; /me must not add another.
    assert len(logs) == 1
