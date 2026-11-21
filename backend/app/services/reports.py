"""Deterministic PDF/XLSX exports of real, role-scoped ticket rows."""

import io
from datetime import datetime, timezone
from typing import Any

from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas
from sqlalchemy import false, select
from sqlalchemy.orm import Session, selectinload

from app.models import Ticket, User
from app.schemas.reports import ReportMeta, TicketChannel

COLUMNS = [
    "ID",
    "Reference",
    "Subject",
    "Status",
    "Priority",
    "Channel",
    "Department",
    "Student",
    "Assigned To",
    "Escalated",
    "Created At",
]
CHANNEL_VALUES = [channel.value for channel in TicketChannel]


def _scope_conditions(user: User) -> list[Any]:
    if user.role == "admin":
        return []
    if user.role == "hod":
        if user.department_id is None:
            return [false()]
        return [Ticket.department_id == user.department_id]
    if user.role == "staff":
        return [Ticket.assigned_to == user.id]
    return [false()]


def _scope_label(user: User) -> str:
    if user.role == "admin":
        return "all tickets"
    if user.role == "hod":
        return f"department_id={user.department_id}"
    if user.role == "staff":
        return f"assigned_to={user.id}"
    return "none"


def select_tickets(
    db: Session,
    user: User,
    *,
    status: str | None = None,
    priority: str | None = None,
    department_id: int | None = None,
    student_id: int | None = None,
    assigned_to: int | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    channel: str | None = None,
    is_escalated: bool | None = None,
    skip: int = 0,
    limit: int = 1000,
) -> list[Ticket]:
    """Apply the ticket-list filters and caller scope with real SQL."""
    conditions = _scope_conditions(user)
    if status:
        conditions.append(Ticket.status == status)
    if priority:
        conditions.append(Ticket.priority == priority)
    if department_id is not None:
        conditions.append(Ticket.department_id == department_id)
    if student_id is not None:
        conditions.append(Ticket.student_id == student_id)
    if assigned_to is not None:
        conditions.append(Ticket.assigned_to == assigned_to)
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(Ticket.subject.ilike(pattern) | Ticket.description.ilike(pattern))
    if date_from is not None:
        conditions.append(Ticket.created_at >= date_from)
    if date_to is not None:
        conditions.append(Ticket.created_at <= date_to)
    if channel:
        conditions.append(Ticket.channel == channel)
    if is_escalated is not None:
        conditions.append(Ticket.is_escalated.is_(is_escalated))

    return list(
        db.scalars(
            select(Ticket)
            .where(*conditions)
            .options(
                selectinload(Ticket.student),
                selectinload(Ticket.assignee),
                selectinload(Ticket.department),
            )
            .order_by(Ticket.created_at.desc(), Ticket.id.desc())
            .offset(skip)
            .limit(limit)
        ).all()
    )


def _row_values(ticket: Ticket) -> list[str]:
    return [
        str(ticket.id),
        ticket.public_reference,
        ticket.subject,
        ticket.status,
        ticket.priority,
        ticket.channel,
        ticket.department.name if ticket.department else "",
        ticket.student.full_name if ticket.student else "",
        ticket.assignee.full_name if ticket.assignee else "",
        "yes" if ticket.is_escalated else "no",
        ticket.created_at.isoformat() if ticket.created_at else "",
    ]


def build_pdf(tickets: list[Ticket], meta: ReportMeta) -> bytes:
    """Render a paged PDF; ``invariant`` keeps byte output deterministic."""
    buffer = io.BytesIO()
    pdf = pdf_canvas.Canvas(buffer, pagesize=A4, invariant=1)
    pdf.setTitle("Ticket report")
    width, height = A4
    left = 18 * mm
    line_height = 5.2 * mm
    y = height - 18 * mm

    def new_page() -> None:
        nonlocal y
        pdf.showPage()
        pdf.setFont("Helvetica", 9)
        y = height - 18 * mm

    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(left, y, "Ticket report")
    y -= 8 * mm
    pdf.setFont("Helvetica", 9)
    pdf.drawString(left, y, f"Generated at: {meta.generated_at.isoformat()}")
    y -= line_height
    pdf.drawString(left, y, f"Scope: {meta.scope}")
    y -= line_height
    pdf.drawString(left, y, f"Tickets: {meta.ticket_count}")
    y -= line_height * 2

    def draw_line(text: str, bold: bool = False) -> None:
        nonlocal y
        if y < 18 * mm:
            new_page()
        pdf.setFont("Helvetica-Bold" if bold else "Helvetica", 8)
        # Keep every line inside the page: A4 width minus both margins.
        pdf.drawString(left, y, text[:118])
        y -= line_height

    draw_line(" | ".join(COLUMNS), bold=True)
    for ticket in tickets:
        draw_line(" | ".join(_row_values(ticket)))

    pdf.save()
    return buffer.getvalue()


def build_xlsx(tickets: list[Ticket], meta: ReportMeta) -> bytes:
    """Workbook layout: row 1 generated_at, row 2 scope, row 3 columns, then data."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Tickets"
    sheet.append(["Generated at", meta.generated_at.isoformat()])
    sheet.append(["Scope", meta.scope])
    sheet.append(COLUMNS)
    for ticket in tickets:
        sheet.append(_row_values(ticket))
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def build_meta(tickets: list[Ticket], user: User, *, at: datetime | None = None) -> ReportMeta:
    generated_at = at or datetime.now(timezone.utc)
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    return ReportMeta(
        generated_at=generated_at,
        scope=_scope_label(user),
        ticket_count=len(tickets),
    )
