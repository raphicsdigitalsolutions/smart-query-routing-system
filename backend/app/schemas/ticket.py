"""Ticket, message, history and department API contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import TicketPriority, TicketStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TicketCreate(BaseModel):
    subject: str = Field(min_length=5, max_length=255)
    description: str = Field(min_length=10, max_length=10000)
    department_id: int | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, max_length=80)
    priority: TicketPriority = TicketPriority.NORMAL
    # Auto-routing is deterministic and only used when no department was
    # supplied (or when the caller explicitly asks for a routed department).
    auto_route: bool = False
    channel: str = "web"

    @field_validator("subject", "description")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("channel")
    @classmethod
    def valid_channel(cls, value: str) -> str:
        if value not in {"web", "email", "whatsapp"}:
            raise ValueError("channel must be web, email or whatsapp")
        return value


class TicketUpdate(BaseModel):
    subject: str | None = Field(default=None, min_length=5, max_length=255)
    description: str | None = Field(default=None, min_length=10, max_length=10000)
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    is_escalated: bool | None = None
    department_id: int | None = Field(default=None, gt=0)
    resolution_summary: str | None = Field(default=None, max_length=5000)

    @field_validator("resolution_summary")
    @classmethod
    def strip_summary(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class AssignRequest(BaseModel):
    assignee_id: int | None = Field(default=None, gt=0)


class MessageCreate(BaseModel):
    message_body: str = Field(min_length=1, max_length=10000)
    is_internal: bool = False

    @field_validator("message_body")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class TicketResponse(ORMModel):
    id: int
    public_reference: str
    subject: str
    description: str
    category: str | None
    priority: str
    status: str
    is_escalated: bool
    student_id: int
    assigned_to: int | None
    department_id: int
    student_name: str | None = None
    assignee_name: str | None = None
    department_name: str | None = None
    channel: str = "web"
    auto_routed: bool = False
    escalated_at: datetime | None = None
    first_response_at: datetime | None = None
    resolution_summary: str | None = None
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    success: bool = True
    items: list[TicketResponse]
    total: int
    skip: int
    limit: int


class MessageResponse(ORMModel):
    id: int
    ticket_id: int
    sender_id: int
    sender_name: str | None = None
    message_body: str
    is_internal: bool
    created_at: datetime


class MessageListResponse(BaseModel):
    success: bool = True
    items: list[MessageResponse]
    total: int


class MessageCreatedResponse(BaseModel):
    success: bool = True
    message: MessageResponse


class AttachmentResponse(ORMModel):
    """Safe metadata for a stored ticket attachment; never includes a disk path."""

    id: int
    message_id: int
    file_name: str
    content_type: str
    size_bytes: int
    created_at: datetime


class AttachmentListResponse(BaseModel):
    success: bool = True
    items: list[AttachmentResponse]
    total: int


class StatusHistoryResponse(ORMModel):
    id: int
    from_status: str | None
    to_status: str
    changed_by_id: int | None
    note: str | None
    created_at: datetime


class AssignmentHistoryResponse(ORMModel):
    id: int
    from_assignee_id: int | None
    to_assignee_id: int | None
    changed_by_id: int | None
    created_at: datetime


class TicketHistoryResponse(BaseModel):
    success: bool = True
    status_changes: list[StatusHistoryResponse]
    assignments: list[AssignmentHistoryResponse]


class MutationResponse(BaseModel):
    success: bool = True
    ticket: TicketResponse
    message: str | None = None


class DepartmentResponse(ORMModel):
    id: int
    name: str
    description: str | None
    is_active: bool


class DepartmentListResponse(BaseModel):
    success: bool = True
    items: list[DepartmentResponse]


class AssignableUserResponse(ORMModel):
    id: int
    full_name: str
    email: str
    role: str
    department_id: int | None = None


class AssignableUserListResponse(BaseModel):
    success: bool = True
    items: list[AssignableUserResponse]


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None
