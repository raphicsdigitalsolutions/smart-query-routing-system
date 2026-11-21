"""API contracts for per-user (BYOK) OpenAI credentials."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ApiKeyUpdate(BaseModel):
    """Request body for adding or replacing a personal provider key."""

    # 256 plaintext characters produce a Fernet token that fits the 512-char
    # encrypted_key column. Oversized values are rejected before encryption.
    api_key: str = Field(min_length=8, max_length=256)

    @field_validator("api_key")
    @classmethod
    def strip_key(cls, value: str) -> str:
        return value.strip()


class ApiKeyStatusResponse(BaseModel):
    """Non-secret configuration status returned by every settings endpoint."""

    success: bool = True
    provider: str = "openai"
    configured: bool = False
    has_key: bool = False
    has_api_key: bool = False
    is_valid: bool = False
    status: str = "not_configured"
    key_hint: str | None = None
    validated_at: datetime | None = None
    last_used_at: datetime | None = None
