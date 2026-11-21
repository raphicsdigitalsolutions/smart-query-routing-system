"""Generic bounded-agent run telemetry with permission outcome."""

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AgentRun(TimestampMixin, Base):
    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'failed', 'abstained')",
            name="agent_run_status_valid",
        ),
        Index("ix_agent_runs_ticket_created", "ticket_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    requested_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    analysis_id: Mapped[int | None] = mapped_column(
        ForeignKey("ticket_ai_analyses.id", ondelete="SET NULL"), nullable=True
    )
    workflow: Mapped[str] = mapped_column(String(80), nullable=False, default="ticket_analysis")
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tool_io_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    permission_outcome: Mapped[str] = mapped_column(
        String(40), nullable=False, default="allowed"
    )
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
