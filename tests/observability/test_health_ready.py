"""Health readiness: 200 when DB and queue (with ping) are available."""

import pytest
from fastapi.testclient import TestClient

from app.adapters.queue.fake_queue import FakeJobQueue
from app.adapters.storage.fake_storage import FakeObjectStorage
from app.api.app import create_app
from app.db.session import get_session_factory


def test_readiness_returns_200_when_deps_available(session_factory):
    """Readiness returns 200 with checks when DB and queue (with ping) are ok."""
    fake_storage = FakeObjectStorage()
    fake_queue = FakeJobQueue()
    app = create_app(storage=fake_storage, queue=fake_queue, session_factory=session_factory)
    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ready"
    assert "checks" in data
    assert data["checks"].get("db") == "ok"
    assert data["checks"].get("redis") == "ok"


def test_liveness_returns_200():
    """Liveness is unchanged: always 200."""
    app = create_app(storage=FakeObjectStorage(), queue=FakeJobQueue(), session_factory=get_session_factory())
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"
