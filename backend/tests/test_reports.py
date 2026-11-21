"""PDF/XLSX exports: magic bytes, real rows, filters and role scoping."""

from datetime import datetime, timedelta, timezone
from io import BytesIO

from openpyxl import load_workbook

from app.api.routes.reports import router as reports_router
from app.core.config import settings
from app.main import app
from app.models import Ticket
from tests.conftest import auth_header

BASE = "/api/v1/reports"

if not any(getattr(route, "path", None) == f"{settings.API_V1_PREFIX}/reports/tickets.pdf" for route in app.routes):
    app.include_router(reports_router, prefix=settings.API_V1_PREFIX)


def submit(client, users, departments, email, department, subject, priority="normal"):
    response = client.post(
        "/api/v1/tickets",
        json={
            "subject": subject,
            "description": "A detailed description used for report filtering checks",
            "department_id": departments[department].id,
            "priority": priority,
        },
        headers=auth_header(client, email),
    )
    assert response.status_code == 201, response.text
    return response.json()


def seed(client, db_session, users, departments):
    registry = submit(client, users, departments, users["student"].email, "registry", "Alpha transcript request")
    other = submit(client, users, departments, users["student"].email, "registry", "Beta scholarship question")
    outside = submit(
        client, users, departments, users["student2"].email, "other", "Gamma IT support issue"
    )
    assigned = client.post(
        f"/api/v1/tickets/{registry['id']}/assign",
        json={"assignee_id": users["staff"].id},
        headers=auth_header(client, users["admin"].email),
    )
    assert assigned.status_code == 200, assigned.text

    row = db_session.get(Ticket, other["id"])
    row.channel = "email"
    row.is_escalated = True
    row.created_at = datetime.now(timezone.utc) - timedelta(days=2)
    db_session.commit()
    return registry, other, outside


def get_report(client, headers, extension="xlsx", **params):
    return client.get(f"{BASE}/tickets.{extension}", params=params or None, headers=headers)


def test_pdf_and_xlsx_magic_and_headers(client, db_session, users, departments) -> None:
    seed(client, db_session, users, departments)
    admin = auth_header(client, users["admin"].email)

    pdf = get_report(client, admin, "pdf")
    assert pdf.status_code == 200, pdf.text
    assert pdf.content.startswith(b"%PDF")
    assert "application/pdf" in pdf.headers["content-type"]
    assert "attachment" in pdf.headers["content-disposition"]
    assert "tickets-report.pdf" in pdf.headers["content-disposition"]
    assert pdf.headers["x-ticket-count"] == "3"

    xlsx = get_report(client, admin, "xlsx")
    assert xlsx.status_code == 200, xlsx.text
    assert xlsx.content[:2] == b"PK"
    assert "spreadsheetml.sheet" in xlsx.headers["content-type"]
    assert "attachment" in xlsx.headers["content-disposition"]
    assert "tickets-report.xlsx" in xlsx.headers["content-disposition"]
    assert xlsx.headers["x-ticket-count"] == "3"


def test_xlsx_header_and_row_counts(client, db_session, users, departments) -> None:
    seed(client, db_session, users, departments)
    admin = auth_header(client, users["admin"].email)
    response = get_report(client, admin, "xlsx")
    workbook = load_workbook(BytesIO(response.content))
    sheet = workbook["Tickets"]
    assert sheet.max_row == 3 + 3  # generated_at, scope, columns, then 3 tickets
    assert sheet["A1"].value == "Generated at"
    assert sheet["A2"].value == "Scope"
    assert sheet["B2"].value == "all tickets"
    assert sheet["A3"].value == "ID"
    subjects = {sheet.cell(row=index, column=3).value for index in range(4, sheet.max_row + 1)}
    assert subjects == {
        "Alpha transcript request",
        "Beta scholarship question",
        "Gamma IT support issue",
    }


def test_role_scoping_in_exports(client, db_session, users, departments) -> None:
    seed(client, db_session, users, departments)

    def subjects(headers):
        response = get_report(client, headers, "xlsx")
        assert response.status_code == 200, response.text
        sheet = load_workbook(BytesIO(response.content))["Tickets"]
        return {sheet.cell(row=i, column=3).value for i in range(4, sheet.max_row + 1)}

    assert subjects(auth_header(client, users["hod"].email)) == {
        "Alpha transcript request",
        "Beta scholarship question",
    }
    assert subjects(auth_header(client, users["staff"].email)) == {"Alpha transcript request"}
    assert get_report(client, auth_header(client, users["student"].email), "pdf").status_code == 403


def test_report_filters(client, db_session, users, departments) -> None:
    seed(client, db_session, users, departments)
    admin = auth_header(client, users["admin"].email)

    def count(**params):
        response = get_report(client, admin, "xlsx", **params)
        assert response.status_code == 200, response.text
        sheet = load_workbook(BytesIO(response.content))["Tickets"]
        return sheet.max_row - 3

    # Assigning the first ticket moves it from "new" to "assigned".
    assert count(status="new") == 2
    assert count(status="assigned") == 1
    assert count(priority="high") == 0
    assert count(department_id=departments["registry"].id) == 2
    assert count(department_id=departments["other"].id) == 1
    assert count(assigned_to=users["staff"].id) == 1
    assert count(assignee_id=users["staff"].id) == 1
    assert count(search="scholarship") == 1
    assert count(search="transcript") == 1
    assert count(channel="email") == 1
    assert count(channel="web") == 2
    assert count(is_escalated="true") == 1
    assert count(is_escalated="false") == 2
    assert count(**{"from": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}) == 2
    assert count(**{"to": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()}) == 1
    assert count(skip=1, limit=1) == 1
    assert count(limit=1) == 1


def test_report_requires_authentication(client) -> None:
    assert client.get(f"{BASE}/tickets.pdf").status_code == 401
    assert client.get(f"{BASE}/tickets.xlsx").status_code == 401
