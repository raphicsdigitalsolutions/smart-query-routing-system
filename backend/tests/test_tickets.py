"""Ticket workflow, role permissions, history and filtering tests."""

from sqlalchemy import select

from app.models import AuditLog, Notification, Ticket, TicketAssignmentHistory, TicketStatusHistory
from tests.conftest import TEST_PASSWORD, auth_header

BASE = "/api/v1/tickets"


def submit(client, users, departments, email="ada@university.edu", **overrides):
    payload = {
        "subject": "Scholarship deadline clarification",
        "description": "Could you please confirm the current request status?",
        "department_id": departments["registry"].id,
    }
    payload.update(overrides)
    return client.post(BASE, json=payload, headers=auth_header(client, email))


def assign(client, ticket_id: int, email: str, assignee_id: int | None):
    return client.post(
        f"{BASE}/{ticket_id}/assign",
        json={"assignee_id": assignee_id},
        headers=auth_header(client, email),
    )


def test_student_creates_ticket_with_reference_history_and_audit(client, db_session, users, departments) -> None:
    response = submit(client, users, departments)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["public_reference"].startswith("TKT-")
    assert body["status"] == "new"
    assert body["priority"] == "normal"
    assert body["student_id"] == users["student"].id
    assert "password" not in body

    ticket = db_session.get(Ticket, body["id"])
    history = db_session.scalars(
        select(TicketStatusHistory).where(TicketStatusHistory.ticket_id == ticket.id)
    ).all()
    assert [(row.from_status, row.to_status) for row in history] == [(None, "new")]
    audit = db_session.scalar(
        select(AuditLog).where(AuditLog.entity_type == "ticket", AuditLog.action == "ticket.created")
    )
    assert audit.actor_id == users["student"].id
    assert audit.is_override is False


def test_public_references_are_unique(client, users, departments) -> None:
    first = submit(client, users, departments).json()
    second = submit(client, users, departments).json()
    assert first["public_reference"] != second["public_reference"]


def test_student_isolation_and_id_guessing(client, users, departments) -> None:
    own = submit(client, users, departments).json()
    other = submit(client, users, departments, email=users["student2"].email).json()
    headers = auth_header(client, users["student"].email)

    listing = client.get(BASE, headers=headers).json()
    assert [item["id"] for item in listing["items"]] == [own["id"]]

    assert client.get(f"{BASE}/{own['id']}", headers=headers).status_code == 200
    hidden = client.get(f"{BASE}/{other['id']}", headers=headers)
    assert hidden.status_code == 404
    assert hidden.json()["code"] == "not_found"


def test_student_cannot_assign_patch_or_write_internal_notes(client, users, departments) -> None:
    ticket = submit(client, users, departments).json()
    student_headers = auth_header(client, users["student"].email)

    assert client.post(
        f"{BASE}/{ticket['id']}/assign", json={"assignee_id": users["staff"].id}, headers=student_headers
    ).status_code == 403
    assert client.patch(
        f"{BASE}/{ticket['id']}", json={"status": "in_progress"}, headers=student_headers
    ).status_code == 403
    assert client.post(
        f"{BASE}/{ticket['id']}/messages",
        json={"message_body": "private", "is_internal": True},
        headers=student_headers,
    ).status_code == 403


def test_staff_queue_and_assignment_restrictions(client, users, departments) -> None:
    assigned = submit(client, users, departments).json()
    unassigned = submit(client, users, departments, email=users["student2"].email).json()
    staff_headers = auth_header(client, users["staff"].email)

    assert client.get(BASE, headers=staff_headers).json()["items"] == []
    assert client.get(f"{BASE}/{unassigned['id']}", headers=staff_headers).status_code == 404
    assert client.post(
        f"{BASE}/{assigned['id']}/assign",
        json={"assignee_id": users["staff"].id},
        headers=staff_headers,
    ).status_code == 403

    response = assign(client, assigned["id"], users["hod"].email, users["staff"].id)
    assert response.status_code == 200, response.text
    assert response.json()["ticket"]["status"] == "assigned"
    assert response.json()["ticket"]["assigned_to"] == users["staff"].id

    listing = client.get(BASE, headers=staff_headers).json()
    assert [item["id"] for item in listing["items"]] == [assigned["id"]]


def test_assignment_history_and_auto_status_transitions(client, db_session, users, departments) -> None:
    ticket = submit(client, users, departments).json()
    assert assign(client, ticket["id"], users["admin"].email, users["staff"].id).status_code == 200
    assert assign(client, ticket["id"], users["admin"].email, users["staff2"].id).status_code == 200
    assert assign(client, ticket["id"], users["admin"].email, None).status_code == 200

    rows = db_session.scalars(
        select(TicketAssignmentHistory)
        .where(TicketAssignmentHistory.ticket_id == ticket["id"])
        .order_by(TicketAssignmentHistory.id)
    ).all()
    assert [(row.from_assignee_id, row.to_assignee_id) for row in rows] == [
        (None, users["staff"].id),
        (users["staff"].id, users["staff2"].id),
        (users["staff2"].id, None),
    ]
    assert db_session.get(Ticket, ticket["id"]).status == "new"


def test_staff_status_transitions_and_invalid_transition(client, db_session, users, departments) -> None:
    ticket = submit(client, users, departments).json()
    assign(client, ticket["id"], users["admin"].email, users["staff"].id)
    staff_headers = auth_header(client, users["staff"].email)

    changed = client.patch(
        f"{BASE}/{ticket['id']}", json={"status": "in_progress"}, headers=staff_headers
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["ticket"]["status"] == "in_progress"

    # NEW is not reachable from IN_PROGRESS in the controlled lifecycle.
    invalid = client.patch(f"{BASE}/{ticket['id']}", json={"status": "new"}, headers=staff_headers)
    assert invalid.status_code == 409
    assert invalid.json()["code"] == "invalid_status_transition"

    terminated = client.patch(
        f"{BASE}/{ticket['id']}",
        json={"status": "resolved", "resolution_summary": "Confirmed the deadline with Records."},
        headers=staff_headers,
    )
    assert terminated.status_code == 200
    illegal = client.patch(f"{BASE}/{ticket['id']}", json={"status": "assigned"}, headers=staff_headers)
    assert illegal.status_code == 409
    assert illegal.json()["code"] == "invalid_status_transition"

    audits = db_session.scalars(
        select(AuditLog).where(AuditLog.action == "ticket.status_changed")
    ).all()
    assert len(audits) >= 2


def test_hod_department_scope_and_assignment_limits(client, users, departments) -> None:
    in_dept = submit(client, users, departments).json()
    outside = submit(client, users, departments, email=users["student2"].email, **{
        "department_id": departments["other"].id
    }).json()
    hod_headers = auth_header(client, users["hod"].email)

    visible = client.get(BASE, headers=hod_headers).json()
    assert [item["id"] for item in visible["items"]] == [in_dept["id"]]
    assert client.get(f"{BASE}/{outside['id']}", headers=hod_headers).status_code == 404

    assert assign(client, in_dept["id"], users["hod"].email, users["staff2"].id).status_code == 200
    cross = assign(client, in_dept["id"], users["hod"].email, users["hod_other"].id)
    assert cross.status_code == 403

    escalation = client.patch(
        f"{BASE}/{in_dept['id']}", json={"is_escalated": True, "priority": "urgent"}, headers=hod_headers
    )
    assert escalation.status_code == 200
    assert escalation.json()["ticket"]["is_escalated"] is True


def test_admin_sees_all_and_manages_departments(client, users, departments) -> None:
    first = submit(client, users, departments).json()
    submit(client, users, departments, email=users["student2"].email)
    admin_headers = auth_header(client, users["admin"].email)

    assert client.get(BASE, headers=admin_headers).json()["total"] == 2
    moved = client.patch(
        f"{BASE}/{first['id']}",
        json={"department_id": departments["scholarships"].id, "subject": "Corrected subject line"},
        headers=admin_headers,
    )
    assert moved.status_code == 200
    assert moved.json()["ticket"]["department_name"] == "Scholarships"

    created = client.post(
        "/api/v1/departments",
        json={"name": "Student Housing", "description": "Accommodation"},
        headers=admin_headers,
    )
    assert created.status_code == 201
    assert any(
        item["name"] == "Student Housing"
        for item in client.get("/api/v1/departments", headers=admin_headers).json()["items"]
    )

    student_headers = auth_header(client, users["student"].email)
    assert client.post(
        "/api/v1/departments", json={"name": "Nope"}, headers=student_headers
    ).status_code == 403


def test_internal_notes_hidden_from_students(client, db_session, users, departments) -> None:
    ticket = submit(client, users, departments).json()
    assign(client, ticket["id"], users["hod"].email, users["staff"].id)

    staff_headers = auth_header(client, users["staff"].email)
    reply = client.post(
        f"{BASE}/{ticket['id']}/messages",
        json={"message_body": "Please upload your transcript.", "is_internal": False},
        headers=staff_headers,
    )
    assert reply.status_code == 201
    note = client.post(
        f"{BASE}/{ticket['id']}/messages",
        json={"message_body": "Student is eligible; prioritize.", "is_internal": True},
        headers=staff_headers,
    )
    assert note.status_code == 201

    student_messages = client.get(
        f"{BASE}/{ticket['id']}/messages", headers=auth_header(client, users["student"].email)
    ).json()
    assert student_messages["total"] == 1
    assert all(item["is_internal"] is False for item in student_messages["items"])
    assert "prioritize" not in str(student_messages)

    staff_messages = client.get(f"{BASE}/{ticket['id']}/messages", headers=staff_headers).json()
    assert staff_messages["total"] == 2
    assert any(item["is_internal"] is True for item in staff_messages["items"])

    audit = db_session.scalars(
        select(AuditLog).where(AuditLog.action == "message.created")
    ).all()
    assert len(audit) == 2


def test_student_reply_on_own_ticket(client, users, departments) -> None:
    ticket = submit(client, users, departments).json()
    response = client.post(
        f"{BASE}/{ticket['id']}/messages",
        json={"message_body": "I have attached the requested document."},
        headers=auth_header(client, users["student"].email),
    )
    assert response.status_code == 201
    assert response.json()["message"]["is_internal"] is False


def test_closed_ticket_rejects_messages(client, users, departments) -> None:
    ticket = submit(client, users, departments).json()
    admin_headers = auth_header(client, users["admin"].email)
    assign(client, ticket["id"], users["admin"].email, users["staff"].id)
    assert client.patch(
        f"{BASE}/{ticket['id']}", json={"status": "in_progress"}, headers=admin_headers
    ).status_code == 200
    assert client.patch(
        f"{BASE}/{ticket['id']}",
        json={"status": "resolved", "resolution_summary": "No further action required."},
        headers=admin_headers,
    ).status_code == 200
    assert client.patch(
        f"{BASE}/{ticket['id']}", json={"status": "closed"}, headers=admin_headers
    ).status_code == 200

    reply = client.post(
        f"{BASE}/{ticket['id']}/messages", json={"message_body": "Too late"}, headers=admin_headers
    )
    assert reply.status_code == 409
    assert reply.json()["code"] == "ticket_closed"


def test_assignable_user_lookup_is_role_scoped(client, users) -> None:
    admin_items = client.get(
        "/api/v1/users/assignable", headers=auth_header(client, users["admin"].email)
    ).json()["items"]
    assert {item["email"] for item in admin_items} >= {
        users["staff"].email,
        users["hod"].email,
        users["hod_other"].email,
        users["admin"].email,
    }
    assert users["student"].email not in {item["email"] for item in admin_items}

    staff_items = client.get(
        "/api/v1/users/assignable", headers=auth_header(client, users["staff"].email)
    )
    assert staff_items.status_code == 200, staff_items.text
    assert {item["email"] for item in staff_items.json()["items"]} >= {
        users["staff"].email,
        users["hod"].email,
        users["admin"].email,
    }

    hod_items = client.get(
        "/api/v1/users/assignable", headers=auth_header(client, users["hod"].email)
    ).json()["items"]
    assert {item["email"] for item in hod_items} == {
        users["staff"].email,
        users["staff2"].email,
        users["hod"].email,
    }
    assert client.get(
        "/api/v1/users/assignable", headers=auth_header(client, users["student"].email)
    ).status_code == 403


def test_pagination_filtering_and_history_endpoint(client, users, departments) -> None:
    submit(client, users, departments, subject="Alpha transcript request", priority="high")
    submit(client, users, departments, subject="Beta transcript request", priority="low")
    third = submit(client, users, departments, subject="Gamma scholarship question").json()
    admin_headers = auth_header(client, users["admin"].email)

    paged = client.get(f"{BASE}?skip=1&limit=1", headers=admin_headers).json()
    assert paged["total"] == 3 and len(paged["items"]) == 1
    assert paged["skip"] == 1 and paged["limit"] == 1

    filtered = client.get(f"{BASE}?status=new&priority=high", headers=admin_headers).json()
    assert [item["subject"] for item in filtered["items"]] == ["Alpha transcript request"]

    searched = client.get(f"{BASE}?search=scholarship", headers=admin_headers).json()
    assert [item["id"] for item in searched["items"]] == [third["id"]]

    too_many = client.get(f"{BASE}?limit=101", headers=admin_headers)
    assert too_many.status_code == 422

    history = client.get(f"{BASE}/{third['id']}/history", headers=admin_headers).json()
    assert history["status_changes"][0]["to_status"] == "new"
    assert history["assignments"] == []


def test_auto_routing_selects_department_and_audits(client, db_session, users, departments) -> None:
    response = client.post(
        BASE,
        json={
            "subject": "Scholarships award deadline",
            "description": "Please confirm the scholarships award rules for this term.",
            "auto_route": True,
        },
        headers=auth_header(client, users["student"].email),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["auto_routed"] is True
    assert body["department_id"] == departments["scholarships"].id
    assert body["category"]

    audit = db_session.scalar(
        select(AuditLog).where(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == str(body["id"]),
            AuditLog.action == "ticket.auto_routed",
        )
    )
    assert audit is not None


def test_routing_without_confident_match_returns_400(client, users) -> None:
    response = client.post(
        BASE,
        json={
            "subject": "Qzxq random characters",
            "description": "Vvmm qzxq plmk nothing relevant here at all.",
            "auto_route": True,
        },
        headers=auth_header(client, users["student"].email),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "routing_unresolved"


def test_resolution_summary_is_required_for_resolved(
    client, users, departments
) -> None:
    ticket = submit(client, users, departments).json()
    assign(client, ticket["id"], users["admin"].email, users["staff"].id)
    admin_headers = auth_header(client, users["admin"].email)
    denied = client.patch(
        f"{BASE}/{ticket['id']}", json={"status": "resolved"}, headers=admin_headers
    )
    assert denied.status_code == 400
    assert denied.json()["code"] == "resolution_summary_required"

    allowed = client.patch(
        f"{BASE}/{ticket['id']}",
        json={"status": "resolved", "resolution_summary": "Deadline confirmed."},
        headers=admin_headers,
    )
    assert allowed.status_code == 200
    assert allowed.json()["ticket"]["resolution_summary"] == "Deadline confirmed."


def test_manual_escalation_sets_timestamp(client, db_session, users, departments) -> None:
    ticket = submit(client, users, departments).json()
    response = client.patch(
        f"{BASE}/{ticket['id']}",
        json={"is_escalated": True},
        headers=auth_header(client, users["admin"].email),
    )
    assert response.status_code == 200
    assert response.json()["ticket"]["escalated_at"] is not None
    assert db_session.get(Ticket, ticket["id"]).escalated_at is not None


def test_first_public_staff_reply_sets_first_response_at(
    client, db_session, users, departments
) -> None:
    ticket = submit(client, users, departments).json()
    assign(client, ticket["id"], users["admin"].email, users["staff"].id)
    staff_headers = auth_header(client, users["staff"].email)

    client.post(
        f"{BASE}/{ticket['id']}/messages",
        json={"message_body": "Private working note only.", "is_internal": True},
        headers=staff_headers,
    )
    assert db_session.get(Ticket, ticket["id"]).first_response_at is None

    client.post(
        f"{BASE}/{ticket['id']}/messages",
        json={"message_body": "Hello, we are reviewing your request.", "is_internal": False},
        headers=staff_headers,
    )
    assert db_session.get(Ticket, ticket["id"]).first_response_at is not None

    student_rows = db_session.scalars(
        select(Notification).where(
            Notification.recipient_user_id == users["student"].id,
            Notification.ticket_id == ticket["id"],
        )
    ).all()
    assert student_rows
    assert all("Private working note" not in row.body for row in student_rows)
