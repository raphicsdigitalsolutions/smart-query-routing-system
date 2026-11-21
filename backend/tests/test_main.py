"""Smoke tests for the Phase 1 API surface."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "Smart Query Routing System API is running",
        "version": "1.0.0",
    }


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"success": True, "status": "healthy"}


def test_versioned_api_status_endpoint() -> None:
    response = client.get("/api/v1/status")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["version"] == "1.0.0"
    assert body["api_prefix"] == "/api/v1"


def test_unknown_route_uses_structured_error_body() -> None:
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert "error" in body
