"""Request/response contracts for inbound intake adapters and status flags."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IntegrationStatusResponse(BaseModel):
    """Non-sensitive configuration flags only - never secrets or addresses."""

    success: bool = True
    smtp: bool
    whatsapp: bool
    google_oauth: bool
    intake_webhook: bool


class EmailInboundRequest(BaseModel):
    """An inbound email forwarded by a trusted mail adapter.

    ``student_email`` is an explicit mapping field supplied by the caller. The
    untrusted ``from_email`` header is recorded for context but is never used
    to identify or create a user.
    """

    student_email: str = Field(min_length=3, max_length=255)
    subject: str = Field(min_length=5, max_length=255)
    body: str = Field(min_length=10, max_length=10000)
    from_email: str | None = Field(default=None, max_length=255)
    department_id: int | None = Field(default=None, gt=0)
    auto_route: bool = True

    @field_validator("student_email", "subject", "body")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class WhatsAppInboundRequest(BaseModel):
    """An inbound WhatsApp message forwarded by a trusted webhook adapter."""

    student_email: str = Field(min_length=3, max_length=255)
    body: str = Field(min_length=10, max_length=10000)
    from_phone: str | None = Field(default=None, max_length=40)
    student_phone: str | None = Field(default=None, max_length=40)
    department_id: int | None = Field(default=None, gt=0)
    auto_route: bool = True

    @field_validator("student_email", "body")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class EscalationRunResponse(BaseModel):
    success: bool = True
    scanned: int
    escalated: int
