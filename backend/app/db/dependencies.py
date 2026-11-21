"""FastAPI dependencies and safe database probing."""

import logging
from collections.abc import Iterator

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import SessionLocal, engine

logger = logging.getLogger(__name__)


class DatabaseUnavailableError(AppError):
    """Raised when the database cannot be reached (never leaks connection details)."""

    def __init__(self) -> None:
        super().__init__(
            "Database is currently unavailable",
            status_code=503,
            code="database_unavailable",
        )


def get_db() -> Iterator[Session]:
    """Yield a session and guarantee rollback/close on failure."""
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> None:
    """Execute a minimal query; translate driver errors into a safe API error."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        # Log only the exception class: messages can contain connection details.
        logger.warning("Database connection check failed: %s", type(exc).__name__)
        raise DatabaseUnavailableError() from exc
