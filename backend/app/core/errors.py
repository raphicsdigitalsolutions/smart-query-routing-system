"""Application error types and JSON response helpers."""

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.schemas.common import ErrorResponse


class AppError(Exception):
    """Base exception for expected application-level failures.

    Raise this from services or routes to produce a consistent error payload.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        *,
        detail: object = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail
        self.code = code


class NotFoundError(AppError):
    def __init__(self, resource: str) -> None:
        super().__init__(
            f"{resource} not found",
            status_code=404,
            code="not_found",
        )


def safe_exception_summary(exc: BaseException, context: str) -> str:
    """Summarize a failure without retaining provider text or secret material.

    Raw exception messages can contain tokens, URLs with credentials, or provider
    diagnostics. Only the exception class name is retained so operators can still
    distinguish failure categories without storing or exposing sensitive text.
    """
    class_name = type(exc).__name__
    return f"{context} failed ({class_name})"


def error_response(
    *,
    status_code: int,
    error: str,
    detail: object = None,
    code: str | None = None,
) -> JSONResponse:
    """Build a JSONResponse using the shared ErrorResponse contract."""
    body = ErrorResponse(error=error, detail=detail, code=code)
    return JSONResponse(status_code=status_code, content=jsonable_encoder(body))
