"""Response schemas for service status endpoints."""

from pydantic import BaseModel, Field


class RootResponse(BaseModel):
    success: bool = True
    message: str
    version: str


class HealthResponse(BaseModel):
    success: bool = True
    status: str = "healthy"


class ApiStatusResponse(BaseModel):
    success: bool = True
    service: str
    version: str
    api_prefix: str = Field(..., description="Versioned API route prefix")


class DatabaseStatusResponse(BaseModel):
    success: bool = True
    database: str = "connected"
