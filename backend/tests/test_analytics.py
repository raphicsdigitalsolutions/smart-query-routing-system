"""Analytics overview: real aggregates, role scoping and generated_at."""

from datetime import datetime, timedelta, timezone

from app.api.routes.analytics import router as analytics_router
from app.core.config import settings
from app.core.enums import TicketPriority, TicketStatus
from app.main import app
from app.models import Ticket, TicketAiAnalysis
from tests.conftest import auth_header

BASE = "/api/v1/analytics"

# The shared API router is wired by the hosting application; register this
# module explicitly so the test client can reach it in isolation.
if not any(getattr(route, "path", None) == f"{settings.API_V1_PREFIX}/analytics/overview" for route in app.routes):
    app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)


def seed(db_session, users, departments) -> list[Ticket]:
    now = datetime.now(timezone.utc)
    current = now.replace(day=15, hour=12, minute=0, second=0, microsecond=0)
    specs = [
        # ref, dept, status, priority, channel, escalated, assigned_to, age_days, first_response_min
        ("AN-1", "registry", "resolved", "high", "web", True, None, 1, 60),
        ("AN-2", "registry", "new", "normal", "email", False, None, 2, 30),
        ("AN-3", "scholarships", "in_progress", "urgent", "whatsapp", False, None, 40, None),
        ("AN-4", "registry", "closed", "low", "web", False, "staff", 70, 120),
    ]
    rows: list[Ticket] = []
    for ref, dept, status, priority, channel, escalated, assignee, age, response_min in specs:
        created = current - timedelta(days=age)
        row = Ticket(
            public_reference=ref,
            subject=f"Subject {ref}",
            description=f"Description for {ref} used for analytics checks",
            status=status,
            priority=priority,
            channel=channel,
            is_escalated=escalated,
            student_id=users["student"].id,
            assigned_to=users[assignee].id if assignee else None,
            department_id=departments[dept].id,
            created_at=created,
            first_response_at=created + timedelta(minutes=response_min) if response_min else None,
        )
        db_session.add(row)
        rows.append(row)
    db_session.flush()

    # Two versions for AN-1: only the newest category may be counted.
    db_session.add_all(
        [
            TicketAiAnalysis(
                ticket_id=rows[0].id,
                version=1,
                status="completed",
                classification_json={"category": "obsolete"},
            ),
            TicketAiAnalysis(
                ticket_id=rows[0].id,
                version=2,
                status="completed",
                classification_json={"category": "refunds"},
            ),
            TicketAiAnalysis(
                ticket_id=rows[1].id,
                version=1,
                status="completed",
                classification_json={"category": "refunds"},
            ),
            TicketAiAnalysis(
                ticket_id=rows[2].id,
                version=1,
                status="completed",
                classification_json={"category": "admissions"},
            ),
        ]
    )
    db_session.commit()
    return rows


def test_overview_requires_staff_role(client, users) -> None:
    assert client.get(BASE + "/overview").status_code == 401
    student = client.get(BASE + "/overview", headers=auth_header(client, users["student"].email))
    assert student.status_code == 403


def test_admin_overview_uses_real_aggregates(client, db_session, users, departments) -> None:
    seed(db_session, users, departments)
    response = client.get(BASE + "/overview", headers=auth_header(client, users["admin"].email))
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["success"] is True
    assert body["role"] == "admin" and body["scope"] == "all"
    assert "generated_at" in body and body["generated_at"]
    assert body["total_tickets"] == 4
    assert body["status_counts"] == {
        "new": 1,
        "assigned": 0,
        "in_progress": 1,
        "waiting_for_student": 0,
        "resolved": 1,
        "closed": 1,
    }
    assert body["priority_counts"] == {"low": 1, "normal": 1, "high": 1, "urgent": 1}
    assert body["channel_counts"] == {"web": 2, "email": 1, "whatsapp": 1}
    assert body["escalated_count"] == 1
    assert body["resolved_count"] == 1
    assert body["backlog_count"] == 2
    # (60 + 30 + 120) / 3 = 70 minutes, from first_response_at - created_at.
    assert body["avg_first_response_minutes"] == 70.0

    assert sorted(body["department_breakdown"], key=lambda item: item["department_id"]) == sorted(
        [
            {"department_id": departments["registry"].id, "department_name": "Registry", "total": 3},
            {"department_id": departments["scholarships"].id, "department_name": "Scholarships", "total": 1},
        ],
        key=lambda item: item["department_id"],
    )
    assert body["ai_category_breakdown"] == [
        {"category": "refunds", "total": 2},
        {"category": "admissions", "total": 1},
    ]

    assert len(body["monthly_volume"]) == 6
    assert sum(month["total"] for month in body["monthly_volume"]) == 4
    assert body["monthly_volume"][-1]["month"] == datetime.now(timezone.utc).strftime("%Y-%m")


def test_hod_overview_is_department_scoped(client, db_session, users, departments) -> None:
    seed(db_session, users, departments)
    response = client.get(BASE + "/overview", headers=auth_header(client, users["hod"].email))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_tickets"] == 3
    assert body["scope"] == f"department_id={departments['registry'].id}"
    assert body["status_counts"]["in_progress"] == 0
    assert body["escalated_count"] == 1
    assert body["backlog_count"] == 1
    assert body["department_breakdown"] == [
        {"department_id": departments["registry"].id, "department_name": "Registry", "total": 3}
    ]
    assert body["ai_category_breakdown"] == [{"category": "refunds", "total": 2}]

    other = client.get(BASE + "/overview", headers=auth_header(client, users["hod_other"].email))
    assert other.json()["total_tickets"] == 0
    assert other.json()["department_breakdown"] == []
    assert other.json()["avg_first_response_minutes"] is None


def test_staff_overview_is_limited_to_assigned_tickets(client, db_session, users, departments) -> None:
    seed(db_session, users, departments)
    response = client.get(BASE + "/overview", headers=auth_header(client, users["staff"].email))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_tickets"] == 1
    assert body["scope"] == f"assigned_to={users['staff'].id}"
    assert body["status_counts"]["closed"] == 1
    assert body["priority_counts"]["low"] == 1
    assert body["avg_first_response_minutes"] == 120.0
