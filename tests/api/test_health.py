"""Health endpoints."""

from fastapi.testclient import TestClient


def test_health_live_returns_200(api_client: TestClient):
    """GET /health/live returns 200."""
    response = api_client.get("/health/live")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_health_ready_returns_200(api_client: TestClient):
    """GET /health/ready returns 200."""
    response = api_client.get("/health/ready")
    assert response.status_code == 200
    assert response.json().get("status") == "ready"
