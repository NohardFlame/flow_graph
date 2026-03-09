"""Run creation: create for existing document, reject unknown document, prevent duplicate active run."""

import io
import pytest
from fastapi.testclient import TestClient


def test_create_run_for_existing_document(api_client: TestClient, fake_queue):
    """Create run for an existing document; returns 202 and enqueues payload."""
    # Create document via upload
    upload = api_client.post(
        "/documents",
        files={"file": ("run-test.txt", io.BytesIO(b"content"), "text/plain")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]
    # Create run
    response = api_client.post(f"/documents/{document_id}/runs")
    assert response.status_code == 202
    data = response.json()
    assert data["id"]
    assert data["document_id"] == document_id
    payloads = fake_queue.payloads()
    assert len(payloads) == 1
    assert payloads[0].get("run_id") == data["id"]


def test_create_run_rejects_unknown_document_id(api_client: TestClient):
    """Return 404 for non-existent document."""
    response = api_client.post("/documents/00000000-0000-0000-0000-000000000000/runs")
    assert response.status_code == 404
    assert response.json().get("code") == "not_found"


def test_create_run_prevents_duplicate_active_run(api_client: TestClient, fake_queue):
    """When document already has an active run, return 409."""
    upload = api_client.post(
        "/documents",
        files={"file": ("dup.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["id"]
    first = api_client.post(f"/documents/{document_id}/runs")
    assert first.status_code == 202
    second = api_client.post(f"/documents/{document_id}/runs")
    assert second.status_code == 409
    assert second.json().get("code") == "conflict"
