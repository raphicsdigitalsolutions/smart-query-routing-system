"""Contracts for the admin-only audit log reader."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None = None
    actor_email: str | None = None
    actor_role: str | None = None
    action: str
    entity_type: str
    entity_id: str
    details: dict[str, Any] | None = None
    is_override: bool = False
    created_at: datetime


class AuditLogListResponse(BaseModel):
    success: bool = True
    items: list[AuditLogResponse]
    total: int
    skip: int
    limit: int
