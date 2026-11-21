"""Database layer: engine, sessions, dependencies and declarative base.

Migrations are owned by Alembic; application code must never call
``Base.metadata.create_all()`` outside of isolated tests.
"""

from app.db.base import Base, TimestampMixin
from app.db.dependencies import DatabaseUnavailableError, check_database_connection, get_db
from app.db.session import SessionLocal, create_database_engine, dispose_engine, engine

__all__ = [
    "Base",
    "DatabaseUnavailableError",
    "SessionLocal",
    "TimestampMixin",
    "check_database_connection",
    "create_database_engine",
    "dispose_engine",
    "engine",
    "get_db",
]
