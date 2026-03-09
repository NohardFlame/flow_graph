"""Error handling: structured error responses and correlation id in responses."""

import io
import pytest
from fastapi.testclient import TestClient


def test_internal_exception_becomes_structured_error_response(api_client: TestClient):
    """NotFoundError returns JSON with detail, code, and no stack trace."""
    response = api_client.get("/documents/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data.get("code") == "not_found"
    assert "traceback" not in str(data).lower()
    assert "Traceback" not in str(data)


def test_correlation_id_in_error_response(api_client: TestClient, correlation_id_headers):
    """When X-Request-ID is sent, error response includes it in body and headers."""
    response = api_client.get(
        "/documents/00000000-0000-0000-0000-000000000000",
        headers=correlation_id_headers,
    )
    assert response.status_code == 404
    assert response.headers.get("X-Request-ID") == "test-correlation-id-123"
    data = response.json()
    assert data.get("correlation_id") == "test-correlation-id-123"


def test_correlation_id_in_success_response(api_client: TestClient, correlation_id_headers):
    """When X-Request-ID is sent, success response includes it in headers."""
    response = api_client.get("/health/live", headers=correlation_id_headers)
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "test-correlation-id-123"


def test_validation_error_returns_400(api_client: TestClient):
    """ValidationError (e.g. bad extension) returns 400 with code validation_error."""
    response = api_client.post(
        "/documents",
        files={"file": ("bad.exe", io.BytesIO(b"x"), "application/octet-stream")},
    )
    assert response.status_code == 400
    assert response.json().get("code") == "validation_error"
