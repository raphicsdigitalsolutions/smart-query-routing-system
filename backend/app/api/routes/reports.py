"""PDF/XLSX ticket exports with the ticket-list filter surface."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_staff_or_above
from app.core.enums import TicketPriority, TicketStatus
from app.db.dependencies import get_db
from app.models import User
from app.schemas.reports import TicketChannel
from app.services.reports import (
    CHANNEL_VALUES,
    build_meta,
    build_pdf,
    build_xlsx,
    select_tickets,
)

router = APIRouter(prefix="/reports", tags=["reports"])

PDF_MEDIA_TYPE = "application/pdf"
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _filters(
    status: TicketStatus | None,
    priority: TicketPriority | None,
    department_id: int | None,
    student_id: int | None,
    assigned_to: int | None,
    assignee_id: int | None,
    search: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    channel: TicketChannel | None,
    is_escalated: bool | None,
    escalated: bool | None,
    skip: int,
    limit: int,
) -> dict[str, object]:
    return {
        "status": status.value if status else None,
        "priority": priority.value if priority else None,
        "department_id": department_id,
        "student_id": student_id,
        "assigned_to": assigned_to if assigned_to is not None else assignee_id,
        "search": search,
        "date_from": date_from,
        "date_to": date_to,
        "channel": channel.value if channel else None,
        "is_escalated": is_escalated if is_escalated is not None else escalated,
        "skip": skip,
        "limit": limit,
    }


@router.get("/tickets.pdf")
def export_tickets_pdf(
    status: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    department_id: int | None = Query(default=None, gt=0),
    student_id: int | None = Query(default=None, gt=0),
    assigned_to: int | None = Query(default=None, alias="assigned_to", gt=0),
    assignee_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, max_length=120),
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    channel: TicketChannel | None = None,
    is_escalated: bool | None = Query(default=None, alias="is_escalated"),
    escalated: bool | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=1000, ge=1, le=10000),
    db: Session = Depends(get_db),
    user: User = Depends(require_staff_or_above),
) -> StreamingResponse:
    tickets = select_tickets(
        db,
        user,
        **_filters(
            status,
            priority,
            department_id,
            student_id,
            assigned_to,
            assignee_id,
            search,
            date_from,
            date_to,
            channel,
            is_escalated,
            escalated,
            skip,
            limit,
        ),
    )
    content = build_pdf(tickets, build_meta(tickets, user))
    return StreamingResponse(
        iter([content]),
        media_type=PDF_MEDIA_TYPE,
        headers={
            "Content-Disposition": 'attachment; filename="tickets-report.pdf"',
            "X-Ticket-Count": str(len(tickets)),
        },
    )


@router.get("/tickets.xlsx")
def export_tickets_xlsx(
    status: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    department_id: int | None = Query(default=None, gt=0),
    student_id: int | None = Query(default=None, gt=0),
    assigned_to: int | None = Query(default=None, alias="assigned_to", gt=0),
    assignee_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, max_length=120),
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    channel: TicketChannel | None = None,
    is_escalated: bool | None = Query(default=None, alias="is_escalated"),
    escalated: bool | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=1000, ge=1, le=10000),
    db: Session = Depends(get_db),
    user: User = Depends(require_staff_or_above),
) -> StreamingResponse:
    tickets = select_tickets(
        db,
        user,
        **_filters(
            status,
            priority,
            department_id,
            student_id,
            assigned_to,
            assignee_id,
            search,
            date_from,
            date_to,
            channel,
            is_escalated,
            escalated,
            skip,
            limit,
        ),
    )
    content = build_xlsx(tickets, build_meta(tickets, user))
    return StreamingResponse(
        iter([content]),
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": 'attachment; filename="tickets-report.xlsx"',
            "X-Ticket-Count": str(len(tickets)),
        },
    )
