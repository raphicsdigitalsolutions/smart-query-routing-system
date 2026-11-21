"""API contracts for governed knowledge documents.

Responses deliberately contain no filesystem paths: documents are stored in the
database and only their logical metadata and extracted text are exposed.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class KnowledgeDocumentResponse(ORMModel):
    """Metadata and extracted content for one version of a knowledge source."""

    id: int
    title: str
    source_key: str
    version: int
    source_type: str
    file_name: str | None = None
    mime_type: str | None = None
    checksum: str
    content_text: str
    department_id: int | None = None
    uploaded_by_id: int
    uploader_name: str | None = None
    approved_by_id: int | None = None
    approver_name: str | None = None
    approved_at: datetime | None = None
    is_approved: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class KnowledgeListResponse(BaseModel):
    success: bool = True
    items: list[KnowledgeDocumentResponse]
    total: int
    skip: int
    limit: int


class KnowledgeVersionListResponse(BaseModel):
    success: bool = True
    source_key: str
    items: list[KnowledgeDocumentResponse]
    total: int


class KnowledgeUpdate(BaseModel):
    """PATCH payload. Omitted fields are left unchanged."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    content_text: str | None = Field(default=None, min_length=1, max_length=200000)
    is_approved: bool | None = None
    is_active: bool | None = None
    department_id: int | None = Field(default=None, gt=0)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class KnowledgeUploadRequest(BaseModel):
    """Descriptive contract for the multipart upload fields."""

    title: str = Field(min_length=1, max_length=255)
    source_type: str = Field(default="text", max_length=20)
    source_key: str | None = Field(default=None, max_length=255)
    content: str | None = Field(default=None, max_length=200000)
    department_id: int | None = Field(default=None, gt=0)
