"""SQLAlchemy engine, session factory and lifecycle helpers."""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def create_database_engine(url: str | None = None, *, echo: bool | None = None) -> Engine:
    """Build an engine from centralized settings.

    Pool options are only applied to server backends (e.g. PostgreSQL) so the
    same helper can create simple SQLite engines in tests.
    """
    database_url = url or settings.DATABASE_URL
    options: dict[str, object] = {
        "pool_pre_ping": True,
        "echo": settings.DB_ECHO if echo is None else echo,
    }
    if make_url(database_url).get_backend_name() != "sqlite":
        options.update(
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_timeout=settings.DB_POOL_TIMEOUT,
        )
    return create_engine(database_url, **options)


engine = create_database_engine()

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def dispose_engine() -> None:
    """Release pooled connections during application shutdown."""
    engine.dispose()
