"""Read endpoints: 404 for unknown ids, paginate chunks/actions, map internal status to public enum."""

import io
import pytest
from fastapi.testclient import TestClient


def test_get_document_404(api_client: TestClient):
    """Return 404 for unknown document id."""
    response = api_client.get("/documents/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json().get("code") == "not_found"


def test_get_run_404(api_client: TestClient):
    """Return 404 for unknown run id."""
    response = api_client.get("/runs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json().get("code") == "not_found"


def test_get_document_200(api_client: TestClient):
    """Return document metadata after upload."""
    upload = api_client.post(
        "/documents",
        files={"file": ("get-doc.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]
    response = api_client.get(f"/documents/{doc_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == doc_id
    assert data["original_filename"] == "get-doc.txt"
    assert data["size_bytes"] == 1


def test_get_run_maps_internal_status_to_public_enum(api_client: TestClient, fake_queue):
    """Run response has public status (e.g. queued), not internal step names."""
    upload = api_client.post(
        "/documents",
        files={"file": ("status.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert upload.status_code == 201
    doc_id = upload.json()["id"]
    run_resp = api_client.post(f"/documents/{doc_id}/runs")
    assert run_resp.status_code == 202
    run_id = run_resp.json()["id"]
    get_run = api_client.get(f"/runs/{run_id}")
    assert get_run.status_code == 200
    data = get_run.json()
    assert data["status"] == "queued"
    assert "current_step" not in data


def test_get_run_chunks_paginated(api_client_shared_session, fake_queue):
    """Chunks endpoint returns paginated list; 404 for unknown run."""
    from app.db.repositories import DocumentRepository, RunRepository
    from tests.db.conftest import (
        document_factory,
        document_version_factory,
        run_factory,
        chunk_factory,
    )
    api_client, session = api_client_shared_session
    doc_id = "11111111-1111-1111-1111-111111111111"
    ver_id = "22222222-2222-2222-2222-222222222222"
    run_id = "33333333-3333-3333-3333-333333333333"
    doc_repo = DocumentRepository(session)
    run_repo = RunRepository(session)
    doc = document_factory(doc_id)
    doc_repo.save(doc)
    ver = document_version_factory(ver_id, doc_id, source_storage_key="raw/x")
    session.add(ver)
    session.flush()
    run = run_factory(run_id, doc_id, ver_id, status="queued")
    run_repo.save(run)
    for i in range(3):
        session.add(chunk_factory(run_id, f"hash{i}", f"text{i}"))
    session.flush()
    response = api_client.get(f"/runs/{run_id}/chunks?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) == 2
    response2 = api_client.get(f"/runs/{run_id}/chunks?limit=2&offset=2")
    assert response2.status_code == 200
    assert len(response2.json()["items"]) == 1


def test_get_run_chunks_404_for_unknown_run(api_client: TestClient):
    """Chunks for unknown run_id return 404."""
    response = api_client.get("/runs/00000000-0000-0000-0000-000000000000/chunks")
    assert response.status_code == 404


def test_get_run_actions_paginated(api_client_shared_session):
    """Actions endpoint returns paginated list."""
    from app.db.repositories import DocumentRepository, RunRepository
    from tests.db.conftest import (
        document_factory,
        document_version_factory,
        run_factory,
        action_factory,
    )
    api_client, session = api_client_shared_session
    doc_id = "44444444-4444-4444-4444-444444444444"
    ver_id = "55555555-5555-5555-5555-555555555555"
    run_id = "66666666-6666-6666-6666-666666666666"
    doc_repo = DocumentRepository(session)
    run_repo = RunRepository(session)
    doc = document_factory(doc_id)
    doc_repo.save(doc)
    ver = document_version_factory(ver_id, doc_id, source_storage_key="raw/y")
    session.add(ver)
    session.flush()
    run = run_factory(run_id, doc_id, ver_id, status="completed")
    run_repo.save(run)
    for i in range(2):
        session.add(action_factory(f"action-{i}", run_id, f"Label{i}", f"canonical_{i}"))
    session.flush()
    response = api_client.get(f"/runs/{run_id}/actions?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_get_run_actions_404_for_unknown_run(api_client: TestClient):
    """Actions for unknown run_id return 404."""
    response = api_client.get("/runs/00000000-0000-0000-0000-000000000000/actions")
    assert response.status_code == 404
