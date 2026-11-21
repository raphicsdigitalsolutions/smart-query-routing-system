"""Ticket entity - a student query moving through the controlled workflow."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="priority_valid",
        ),
        CheckConstraint(
            "status IN ('new', 'assigned', 'in_progress', 'waiting_for_student', 'resolved', 'closed')",
            name="status_valid",
        ),
        Index("ix_tickets_department_status", "department_id", "status"),
        Index("ix_tickets_student_created", "student_id", "created_at"),
        Index("ix_tickets_escalated_status", "is_escalated", "status"),
        CheckConstraint(
            "channel IN ('web', 'email', 'whatsapp')",
            name="channel_valid",
        ),
        Index("ix_tickets_channel_created", "channel", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    public_reference: Mapped[str] = mapped_column(
        String(32), nullable=False, unique=True, index=True
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(80), nullable=True)
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, default="normal", server_default="normal"
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="new", server_default="new"
    )
    is_escalated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    channel: Mapped[str] = mapped_column(
        String(20), nullable=False, default="web", server_default="web"
    )
    auto_routed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    student: Mapped["User"] = relationship(
        foreign_keys=[student_id], back_populates="tickets_submitted"
    )
    assignee: Mapped["User"] = relationship(
        foreign_keys=[assigned_to], back_populates="tickets_assigned"
    )
    department: Mapped["Department"] = relationship(back_populates="tickets")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    status_history: Mapped[list["TicketStatusHistory"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
    assignment_history: Mapped[list["TicketAssignmentHistory"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )
