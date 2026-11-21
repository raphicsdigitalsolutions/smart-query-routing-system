"""Announcement request/response contracts (admin-managed broadcasts)."""

from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.core.enums import UserRole


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    body: str = Field(min_length=1, max_length=10000)
    # A typed enum makes unknown roles a serialisable Pydantic 422 (ctx values
    # stay JSON-safe) instead of a ValueError that the app-wide error handler
    # cannot encode.
    audience_roles: list[UserRole] = Field(
        min_length=1,
        max_length=len(UserRole),
        validation_alias=AliasChoices("audience_roles", "audience_roles_json"),
    )
    department_id: int | None = Field(default=None, gt=0)
    is_active: bool = True

    @field_validator("title", "body")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    body: str | None = Field(default=None, min_length=1, max_length=10000)
    audience_roles: list[UserRole] | None = Field(
        default=None,
        min_length=1,
        max_length=len(UserRole),
        validation_alias=AliasChoices("audience_roles", "audience_roles_json"),
    )
    department_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @field_validator("title", "body")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    audience_roles: list[str]
    department_id: int | None = None
    created_by_id: int
    published_at: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AnnouncementListResponse(BaseModel):
    success: bool = True
    items: list[AnnouncementResponse]
    total: int
