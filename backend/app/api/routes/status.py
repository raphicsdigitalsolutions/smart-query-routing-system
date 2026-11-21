"""Versioned API routes for service metadata."""

from fastapi import APIRouter

from app.core.config import settings
from app.db.dependencies import check_database_connection
from app.schemas.status import ApiStatusResponse, DatabaseStatusResponse

router = APIRouter(tags=["status"])


@router.get("/status", response_model=ApiStatusResponse)
async def get_api_status() -> ApiStatusResponse:
    """Return basic metadata about the running API version."""
    return ApiStatusResponse(
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        api_prefix=settings.API_V1_PREFIX,
    )


@router.get("/status/database", response_model=DatabaseStatusResponse)
def get_database_status() -> DatabaseStatusResponse:
    """Readiness probe. Returns 503 without connection details when PostgreSQL is down."""
    check_database_connection()
    return DatabaseStatusResponse(database="connected")
