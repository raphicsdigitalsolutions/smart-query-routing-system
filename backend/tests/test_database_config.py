"""Tests for centralized database configuration and session wiring."""

from sqlalchemy.engine import make_url

from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, create_database_engine, engine


def test_database_url_uses_psycopg_driver() -> None:
    assert settings.DATABASE_URL.startswith("postgresql+psycopg://")
    assert settings.DB_POOL_SIZE >= 1
    assert settings.DB_POOL_TIMEOUT >= 1


def test_application_engine_matches_settings() -> None:
    assert engine.url == make_url(settings.DATABASE_URL)
    assert engine.url.drivername == "postgresql+psycopg"


def test_session_factory_is_bound_to_shared_engine() -> None:
    with SessionLocal() as session:
        assert session.get_bind() is engine


def test_engine_helper_can_build_isolated_sqlite_engine() -> None:
    sqlite_engine = create_database_engine("sqlite://")
    try:
        assert sqlite_engine.dialect.name == "sqlite"
    finally:
        sqlite_engine.dispose()


def test_metadata_registers_all_domain_tables() -> None:
    assert {"departments", "users", "tickets", "messages"}.issubset(Base.metadata.tables)
