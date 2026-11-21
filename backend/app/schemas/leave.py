"""Instructor leave request/response contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LeaveBase(BaseModel):
    start_at: datetime
    end_at: datetime
    reason: str | None = Field(default=None, max_length=2000)
    auto_reply: str = Field(min_length=1, max_length=2000)
    is_active: bool = True


class LeaveCreate(LeaveBase):
    # Omitted means "for the caller". Staff may never supply another user id.
    user_id: int | None = Field(default=None, gt=0)


class LeaveUpdate(BaseModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    reason: str | None = Field(default=None, max_length=2000)
    auto_reply: str | None = Field(default=None, min_length=1, max_length=2000)
    is_active: bool | None = None
    user_id: int | None = Field(default=None, gt=0)


class LeaveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_email: str | None = None
    start_at: datetime
    end_at: datetime
    reason: str | None = None
    auto_reply: str
    is_active: bool
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class LeaveListResponse(BaseModel):
    success: bool = True
    items: list[LeaveResponse]
    total: int


class LeaveMutationResponse(BaseModel):
    success: bool = True
    leave: LeaveResponse
    message: str | None = None
