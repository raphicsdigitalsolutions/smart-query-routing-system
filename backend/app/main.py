"""FastAPI application entry point (Phase 4 authentication and tickets)."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import api_router
from app.core.config import settings
from app.core.errors import AppError, error_response, safe_exception_summary
from app.db.session import dispose_engine
from app.schemas.status import HealthResponse, RootResponse

logger = logging.getLogger(__name__)


def _json_safe(value: object) -> object:
    """Convert Pydantic validation contexts (which may hold exceptions) to JSON."""
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    # Do not stringify arbitrary validation-context objects: they may embed
    # exception messages or request values that should not be echoed.
    return f"<{type(value).__name__}>"


async def _escalation_worker() -> None:
    """Production-only periodic SLA sweep; never started in tests/development."""
    while True:
        await asyncio.sleep(settings.ESCALATION_SWEEP_MINUTES * 60)
        try:
            from app.db.session import SessionLocal
            from app.services.escalation import run_escalation_sweep

            with SessionLocal() as db:
                result = run_escalation_sweep(db)
            logger.info("Escalation sweep finished: %s", result)
        except Exception:
            logger.exception("Escalation sweep failed")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Release pooled database connections when the server shuts down."""
    task = asyncio.create_task(_escalation_worker()) if settings.ENVIRONMENT == "production" else None
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        dispose_engine()
        logger.info("Database connections released")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "API for the University Intelligent Communication Hub. Includes JWT "
        "authentication, role-based authorization and the core ticket workflow."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Local Vite dev server is allowed to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ---------------------------------------------------------------------------
# Error handlers: every failure returns the same {"success": false, ...} shape.
# ---------------------------------------------------------------------------
@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return error_response(
        status_code=exc.status_code,
        error=exc.message,
        detail=exc.detail,
        code=exc.code,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    return error_response(
        status_code=422,
        error="Validation error",
        detail=_json_safe(exc.errors()),
        code="validation_error",
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException):
    error = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return error_response(status_code=exc.status_code, error=error)


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception):
    summary = safe_exception_summary(exc, "Unhandled request error")
    logger.error(summary)
    return error_response(
        status_code=500,
        error="Internal server error",
        detail=summary if settings.DEBUG else None,
        code="internal_error",
    )


# ---------------------------------------------------------------------------
# Root-level status endpoints (unversioned, used by smoke tests and monitors).
# ---------------------------------------------------------------------------
@app.get("/", response_model=RootResponse, tags=["status"])
async def read_root() -> RootResponse:
    return RootResponse(
        message="Smart Query Routing System API is running",
        version=settings.VERSION,
    )


@app.get("/health", response_model=HealthResponse, tags=["status"])
async def health_check() -> HealthResponse:
    """Liveness probe. Deliberately does not touch the database."""
    return HealthResponse(status="healthy")
