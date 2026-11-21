"""Phase 6 AI analysis, draft and approval API contracts."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ticket import MessageResponse


class AiErrorPayload(BaseModel):
    code: str
    message: str


class AiExecutionStep(BaseModel):
    model_config = ConfigDict(extra="allow")

    node: str
    status: str
    duration_ms: int = 0
    detail: str | None = None
    attempts: int | None = None
    model: str | None = None


class AiAnalysisResponse(BaseModel):
    """Persisted result of one bounded agent run."""

    success: bool = True
    id: int
    ticket_id: int
    version: int
    status: str
    is_current: bool
    classification: dict[str, Any] | None = None
    priority_recommendation: str | None = None
    department_recommendation: dict[str, Any] | None = None
    staff_recommendation: dict[str, Any] | None = None
    knowledge_sources: list[dict[str, Any]] = Field(default_factory=list)
    no_evidence: bool = False
    draft: dict[str, Any] | None = None
    validation: dict[str, Any] | None = None
    confidence: float | None = None
    abstention_reason: str | None = None
    error: AiErrorPayload | None = None
    execution_metadata: list[AiExecutionStep] = Field(default_factory=list)
    approved_message_id: int | None = None
    approved_at: datetime | None = None
    created_at: datetime


class AiDraftApprovalResponse(BaseModel):
    """Result of a human approval; message is created by the ticket service."""

    success: bool = True
    analysis_id: int
    message: MessageResponse
    already_approved: bool = False
