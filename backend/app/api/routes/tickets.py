"""Ticket management endpoints with backend-enforced role permissions."""

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    require_hod_or_admin,
    require_student,
)
from app.core.enums import TicketPriority, TicketStatus
from app.db.dependencies import get_db
from app.models import User
from app.schemas.ticket import (
    AssignRequest,
    AttachmentListResponse,
    AttachmentResponse,
    MessageCreate,
    MessageCreatedResponse,
    MessageListResponse,
    MutationResponse,
    TicketCreate,
    TicketHistoryResponse,
    TicketListResponse,
    TicketResponse,
    TicketUpdate,
)
from app.services.attachments import create_message_attachment, list_ticket_attachments
from app.services.tickets import (
    assign_ticket,
    create_message,
    create_ticket,
    get_ticket_detail,
    get_ticket_history,
    list_messages,
    list_tickets,
    update_ticket,
)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def submit_ticket(
    payload: TicketCreate,
    db: Session = Depends(get_db),
    student: User = Depends(require_student),
) -> TicketResponse:
    """Students submit a new query; reference and workflow start are automatic."""
    return create_ticket(db, payload, student)


@router.get("", response_model=TicketListResponse)
def get_tickets(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    ticket_status: TicketStatus | None = Query(default=None, alias="status"),
    priority: TicketPriority | None = None,
    department_id: int | None = Query(default=None, gt=0),
    assignee_id: int | None = Query(default=None, gt=0),
    escalated: bool | None = None,
    search: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TicketListResponse:
    """List only the tickets this role is allowed to see, with filters/pagination."""
    return list_tickets(
        db,
        user,
        skip=skip,
        limit=limit,
        status=ticket_status,
        priority=priority,
        department_id=department_id,
        assignee_id=assignee_id,
        escalated=escalated,
        search=search,
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TicketResponse:
    return get_ticket_detail(db, ticket_id, user)


@router.get("/{ticket_id}/history", response_model=TicketHistoryResponse)
def get_history(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TicketHistoryResponse:
    return get_ticket_history(db, ticket_id, user)


@router.patch("/{ticket_id}", response_model=MutationResponse)
def patch_ticket(
    ticket_id: int,
    payload: TicketUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MutationResponse:
    return update_ticket(db, ticket_id, payload, user)


@router.post("/{ticket_id}/assign", response_model=MutationResponse)
def post_assignment(
    ticket_id: int,
    payload: AssignRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_hod_or_admin),
) -> MutationResponse:
    """HOD assigns within their department; admin may assign any ticket."""
    return assign_ticket(db, ticket_id, payload.assignee_id, user)


@router.post("/{ticket_id}/messages", response_model=MessageCreatedResponse, status_code=status.HTTP_201_CREATED)
def post_message(
    ticket_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageCreatedResponse:
    return MessageCreatedResponse(message=create_message(db, ticket_id, payload, user))


@router.get("/{ticket_id}/messages", response_model=MessageListResponse)
def get_messages(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageListResponse:
    """Students never receive internal staff notes from this endpoint."""
    return list_messages(db, ticket_id, user)


@router.post(
    "/{ticket_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    message_body: str | None = Form(default=None, max_length=10000),
    is_internal: bool = Form(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttachmentResponse:
    """Store a permitted file outside the web root and attach it to a message."""
    return create_message_attachment(
        db,
        ticket_id,
        user,
        file,
        message_body=message_body,
        is_internal=is_internal,
    )


@router.get("/{ticket_id}/attachments", response_model=AttachmentListResponse)
def get_attachments(
    ticket_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AttachmentListResponse:
    """Return attachment metadata only for messages the caller may view."""
    return list_ticket_attachments(db, ticket_id, user)
