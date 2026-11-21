"""Persisted AI analysis, draft and human-approval state for a ticket."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class TicketAiAnalysis(TimestampMixin, Base):
    """One bounded agent run for a ticket.

    Multiple versions may exist (regeneration), but only one is marked current.
    The approval columns are the idempotency boundary for publishing a draft;
    the public message itself is still created by the existing ticket service.
    """

    __tablename__ = "ticket_ai_analyses"
    __table_args__ = (
        UniqueConstraint("ticket_id", "version", name="uq_ticket_ai_analyses_ticket_id_version"),
        CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ai_status_valid",
        ),
        Index("ix_ticket_ai_analyses_ticket_current", "ticket_id", "is_current"),
        Index("ix_ticket_ai_analyses_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    # Structured outputs from the bounded graph. JSON avoids provider-specific types.
    classification_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    priority_recommendation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    department_recommendation_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    staff_recommendation_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    knowledge_sources_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    draft_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    no_evidence: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    abstention_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Sanitized failure details only; prompts, key material and raw responses are never stored.
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_metadata_json: Mapped[list | None] = mapped_column(JSON, nullable=True)

    approved_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
    )
