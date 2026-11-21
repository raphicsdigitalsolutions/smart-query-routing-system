"""Tests for the database readiness probe (mocked - never touches real data)."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

import app.db.dependencies as db_dependencies
from app.api.routes import status as status_routes
from app.db.dependencies import DatabaseUnavailableError
from app.main import app

client = TestClient(app)


def test_database_health_endpoint_reports_connected(monkeypatch) -> None:
    monkeypatch.setattr(status_routes, "check_database_connection", lambda: None)

    response = client.get("/api/v1/status/database")

    assert response.status_code == 200
    assert response.json() == {"success": True, "database": "connected"}


def test_database_health_endpoint_hides_connection_details(monkeypatch) -> None:
    def fail() -> None:
        raise DatabaseUnavailableError()

    monkeypatch.setattr(status_routes, "check_database_connection", fail)

    response = client.get("/api/v1/status/database")

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "database_unavailable"
    assert body["detail"] is None
    assert "smartquery" not in str(body).lower()
    assert "password" not in str(body).lower()


def test_check_database_connection_executes_probe(monkeypatch) -> None:
    fake_engine = MagicMock()
    fake_connection = MagicMock()
    fake_engine.connect.return_value.__enter__.return_value = fake_connection
    monkeypatch.setattr(db_dependencies, "engine", fake_engine)

    db_dependencies.check_database_connection()

    fake_connection.execute.assert_called_once()


def test_check_database_connection_translates_driver_errors(monkeypatch) -> None:
    fake_engine = MagicMock()
    fake_engine.connect.side_effect = OperationalError(
        "SELECT 1", {}, Exception("password=secret@host")
    )
    monkeypatch.setattr(db_dependencies, "engine", fake_engine)

    with pytest.raises(DatabaseUnavailableError) as exc_info:
        db_dependencies.check_database_connection()

    assert exc_info.value.status_code == 503
    assert "secret" not in str(exc_info.value)


def test_get_db_always_closes_the_session(monkeypatch) -> None:
    fake_session = MagicMock()
    monkeypatch.setattr(db_dependencies, "SessionLocal", MagicMock(return_value=fake_session))

    generator = db_dependencies.get_db()
    assert next(generator) is fake_session
    with pytest.raises(StopIteration):
        next(generator)

    fake_session.close.assert_called_once()
