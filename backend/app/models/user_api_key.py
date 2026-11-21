"""Encrypted per-user provider credentials (BYOK)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class UserApiKey(TimestampMixin, Base):
    """One active encrypted API key per user and provider.

    The plaintext key is never persisted. ``key_hint`` is a non-reversible
    suffix intended only for display in the settings UI.
    """

    __tablename__ = "user_api_keys"
    __table_args__ = (
        Index("ix_user_api_keys_user_provider", "user_id", "provider", unique=True),
        UniqueConstraint("user_id", "provider", name="uq_user_api_keys_user_provider"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(
        String(30), nullable=False, default="openai", server_default="openai"
    )
    encrypted_key: Mapped[str] = mapped_column(String(512), nullable=False)
    key_hint: Mapped[str] = mapped_column(String(20), nullable=False)
    is_valid: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
