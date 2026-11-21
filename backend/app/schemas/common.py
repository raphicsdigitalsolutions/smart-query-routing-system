"""Shared response schemas used across API modules."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Consistent JSON body for all non-success responses."""

    success: bool = False
    error: str
    detail: Any | None = None
    code: str | None = Field(default=None, description="Stable machine-readable error code")
