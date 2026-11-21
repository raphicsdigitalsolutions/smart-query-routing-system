"""API contracts for the authenticated notification centre."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(ORMModel):
    id: int
    ticket_id: int | None = None
    recipient_user_id: int | None = None
    recipient_address: str | None = None
    channel: str
    event_type: str
    subject: str | None = None
    body: str
    status: str
    attempts: int = 0
    last_error: str | None = None
    provider_id: str | None = None
    sent_at: datetime | None = None
    read_at: datetime | None = None
    is_internal: bool = False
    created_at: datetime
    updated_at: datetime | None = None


class NotificationListResponse(BaseModel):
    success: bool = True
    items: list[NotificationResponse]
    total: int
    skip: int
    limit: int


class NotificationMarkReadResponse(BaseModel):
    success: bool = True
    notification: NotificationResponse
