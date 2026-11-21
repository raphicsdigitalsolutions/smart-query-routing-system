"""Authenticated AI endpoint tests using isolated SQLite and mocked agent services."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.agents.services import agent_service
from app.agents.tools.knowledge_search import InMemoryKnowledgeRepository
from app.core.config import settings
from app.core.errors import AppError
from app.models import AuditLog, Message, Ticket, TicketAiAnalysis
from tests.ai_helpers import make_llm, sample_analysis, valid_classification, valid_draft, valid_routing
from tests.conftest import auth_header


def _submit_ticket(client, header: dict[str, str], departments: dict) -> int:
    response = client.post(
        "/api/v1/tickets",
        headers=header,
        json={
            "subject": "Password reset question",
            "description": "I cannot access the student portal and need help with my password.",
            "department_id": departments["registry"].id,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _assign(client, admin_header: dict[str, str], ticket_id: int, assignee_id: int) -> None:
    response = client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        headers=admin_header,
        json={"assignee_id": assignee_id},
    )
    assert response.status_code == 200, response.text


def test_student_cannot_access_staff_only_ai_operations(client, users, departments):
    student_header = auth_header(client, "ada@university.edu")
    ticket_id = _submit_ticket(client, student_header, departments)

    analyze = client.post(f"/api/v1/ai/tickets/{ticket_id}/analyze", headers=student_header)
    analysis = client.get(f"/api/v1/ai/tickets/{ticket_id}/analysis", headers=student_header)
    approve = client.post(f"/api/v1/ai/tickets/{ticket_id}/approve-draft", headers=student_header)

    assert analyze.status_code == 403
    assert analysis.status_code == 403
    assert approve.status_code == 403
    assert analyze.json()["code"] == "forbidden"


def test_unassigned_staff_cannot_analyze_ticket(client, users, departments):
    student_header = auth_header(client, "ada@university.edu")
    staff_header = auth_header(client, "grace@university.edu")
    ticket_id = _submit_ticket(client, student_header, departments)

    response = client.post(f"/api/v1/ai/tickets/{ticket_id}/analyze", headers=staff_header)
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_assigned_staff_can_analyze_and_read_analysis(
    client, db_session, monkeypatch, users, departments
):
    student_header = auth_header(client, "ada@university.edu")
    staff_header = auth_header(client, "grace@university.edu")
    admin_header = auth_header(client, "alice@university.edu")
    ticket_id = _submit_ticket(client, student_header, departments)
    _assign(client, admin_header, ticket_id, users["staff"].id)

    analysis = sample_analysis(ticket_id)
    monkeypatch.setattr(agent_service, "run_ticket_analysis", lambda *args, **kwargs: analysis)
    monkeypatch.setattr(agent_service, "get_latest_analysis", lambda *args, **kwargs: analysis)

    created = client.post(f"/api/v1/ai/tickets/{ticket_id}/analyze", headers=staff_header)
    fetched = client.get(f"/api/v1/ai/tickets/{ticket_id}/analysis", headers=staff_header)

    assert created.status_code == 201, created.text
    assert fetched.status_code == 200, fetched.text
    assert created.json()["ticket_id"] == ticket_id
    assert created.json()["success"] is True
    assert fetched.json()["draft"]["needs_staff_review"] is True


def test_assigned_staff_real_workflow_is_not_blocked_by_assignable_user_lookup(
    client, db_session, users, departments
):
    """Regression: the real graph must not 403 when staff request assignable users."""
    student_header = auth_header(client, "ada@university.edu")
    admin_header = auth_header(client, "alice@university.edu")
    ticket_id = _submit_ticket(client, student_header, departments)
    _assign(client, admin_header, ticket_id, users["staff"].id)

    ticket = db_session.get(Ticket, ticket_id)
    staff = db_session.get(type(users["staff"]), users["staff"].id)
    llm, _ = make_llm(
        [
            valid_classification(),
            valid_routing(departments["registry"].id),
            valid_draft(),
        ]
    )

    result = agent_service.run_ticket_analysis(
        db_session,
        ticket_id,
        staff,
        llm=llm,
        knowledge_repository=InMemoryKnowledgeRepository([]),
    )

    assert result.ticket_id == ticket_id
    assert result.status == "completed"
    assert ticket is not None
    stored = db_session.scalar(
        select(TicketAiAnalysis).where(TicketAiAnalysis.ticket_id == ticket_id)
    )
    assert stored is not None
    assert stored.requested_by_id == staff.id


def test_ai_runs_are_rate_limited_per_user(db_session, monkeypatch, users, departments):
    """A durable per-user run counter prevents unbounded AI calls."""
    from app.services.tickets import create_ticket
    from app.schemas.ticket import TicketCreate

    ticket = create_ticket(
        db_session,
        TicketCreate(
            subject="Rate limit verification request",
            description="This description is long enough to pass ticket validation.",
            department_id=departments["registry"].id,
        ),
        users["student"],
    )
    ticket_row = db_session.get(Ticket, ticket.id)
    assert ticket_row is not None
    ticket_row.assigned_to = users["staff"].id
    db_session.commit()
    staff = db_session.get(type(users["staff"]), users["staff"].id)
    monkeypatch.setattr(settings, "AI_RATE_LIMIT_PER_MINUTE", 1)

    llm, _ = make_llm(
        [
            valid_classification(),
            valid_routing(departments["registry"].id),
            valid_draft(),
        ]
    )
    result = agent_service.run_ticket_analysis(
        db_session,
        ticket.id,
        staff,
        llm=llm,
        knowledge_repository=InMemoryKnowledgeRepository([]),
    )
    assert result.status == "completed"

    llm2, _ = make_llm(
        [
            valid_classification(),
            valid_routing(departments["registry"].id),
            valid_draft(),
        ]
    )
    with pytest.raises(AppError) as exc:
        agent_service.run_ticket_analysis(
            db_session,
            ticket.id,
            staff,
            llm=llm2,
            knowledge_repository=InMemoryKnowledgeRepository([]),
        )
    assert exc.value.status_code == 429
    assert exc.value.code == "ai_rate_limited"


def test_staff_approval_creates_one_public_message_and_is_idempotent(
    client, db_session, users, departments
):
    student_header = auth_header(client, "ada@university.edu")
    staff_header = auth_header(client, "grace@university.edu")
    admin_header = auth_header(client, "alice@university.edu")
    ticket_id = _submit_ticket(client, student_header, departments)
    _assign(client, admin_header, ticket_id, users["staff"].id)

    analysis = TicketAiAnalysis(
        ticket_id=ticket_id,
        requested_by_id=users["staff"].id,
        version=1,
        status="completed",
        is_current=True,
        classification_json={},
        draft_json=valid_draft(),
        validation_json={"passed": True, "issues": [], "overall_confidence": 0.76},
        no_evidence=True,
        knowledge_sources_json=[],
        execution_metadata_json=[],
        abstention_reason="No approved knowledge source matched this query.",
    )
    db_session.add(analysis)
    db_session.commit()

    first = client.post(f"/api/v1/ai/tickets/{ticket_id}/approve-draft", headers=staff_header)
    second = client.post(f"/api/v1/ai/tickets/{ticket_id}/approve-draft", headers=staff_header)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["already_approved"] is False
    assert second.json()["already_approved"] is True
    assert second.json()["message"]["id"] == first.json()["message"]["id"]
    assert first.json()["message"]["is_internal"] is False

    messages = db_session.scalar(
        select(func.count()).select_from(Message).where(Message.ticket_id == ticket_id)
    )
    assert messages == 1

    approval_audits = db_session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == str(ticket_id),
            AuditLog.action == "ai.draft_approved",
        )
    )
    message_audits = db_session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.entity_type == "ticket",
            AuditLog.entity_id == str(ticket_id),
            AuditLog.action == "message.created",
        )
    )
    assert approval_audits == 1
    assert message_audits == 1

    stored = db_session.get(TicketAiAnalysis, analysis.id)
    assert stored.approved_by_id == users["staff"].id
    assert stored.approved_at is not None
    assert stored.approved_message_id == first.json()["message"]["id"]


def test_draft_that_failed_validation_cannot_be_published(client, db_session, users, departments):
    student_header = auth_header(client, "ada@university.edu")
    staff_header = auth_header(client, "grace@university.edu")
    admin_header = auth_header(client, "alice@university.edu")
    ticket_id = _submit_ticket(client, student_header, departments)
    _assign(client, admin_header, ticket_id, users["staff"].id)

    analysis = TicketAiAnalysis(
        ticket_id=ticket_id,
        requested_by_id=users["staff"].id,
        version=1,
        status="completed",
        is_current=True,
        classification_json={},
        draft_json=valid_draft(),
        validation_json={"passed": False, "issues": ["Source was not approved."]},
        no_evidence=False,
        knowledge_sources_json=[],
        execution_metadata_json=[],
    )
    db_session.add(analysis)
    db_session.commit()

    response = client.post(f"/api/v1/ai/tickets/{ticket_id}/approve-draft", headers=staff_header)
    assert response.status_code == 409
    assert response.json()["code"] == "ai_validation_failed"

    messages = db_session.scalar(
        select(func.count()).select_from(Message).where(Message.ticket_id == ticket_id)
    )
    assert messages == 0
