"""Startup validation: API and worker exit non-zero on invalid config; readiness 503 when deps down.

Tests use real process startup and real settings loading—no mocks.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.storage.fake_storage import FakeObjectStorage
from app.api.app import create_app

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestAPIExitsNonZeroOnInvalidConfig:
    """API process must fail fast when required config is missing."""

    def test_import_main_without_environment_exits_nonzero(self, subprocess_env_no_environment):
        """Importing app.api.main without ENVIRONMENT raises and exits non-zero."""
        result = subprocess.run(
            [sys.executable, "-c", "from app.api.main import app"],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
            env=subprocess_env_no_environment,
            timeout=10,
        )
        assert result.returncode != 0, (result.stdout, result.stderr)
        assert "ENVIRONMENT" in result.stderr or "configuration" in result.stderr.lower() or "ValidationError" in result.stderr


class TestWorkerExitsNonZeroOnInvalidConfig:
    """Worker process must fail fast when required config is missing."""

    def test_import_arq_worker_without_environment_exits_nonzero(self, subprocess_env_no_environment):
        """Importing worker module without ENVIRONMENT causes non-zero exit (get_settings fails)."""
        result = subprocess.run(
            [sys.executable, "-c", "from app.workers.arq_tasks import WorkerSettings"],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
            env=subprocess_env_no_environment,
            timeout=10,
        )
        assert result.returncode != 0, (result.stdout, result.stderr)
        assert "ENVIRONMENT" in result.stderr or "configuration" in result.stderr.lower() or "ValidationError" in result.stderr


class TestReadinessReportsUnavailableWhenDependencyDown:
    """Readiness endpoint returns 503 when a critical dependency is unavailable."""

    def test_readiness_returns_503_when_queue_ping_fails(self, session_factory):
        """When queue.ping() returns False, GET /health/ready returns 503 with not_ready."""
        class FailingPingQueue:
            def enqueue(self, payload):
                pass

            def ping(self):
                return False

        app = create_app(
            storage=FakeObjectStorage(),
            queue=FailingPingQueue(),
            session_factory=session_factory,
        )
        client = TestClient(app)
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data.get("status") == "not_ready"
        assert data.get("checks", {}).get("redis") == "unavailable"

    def test_readiness_returns_503_when_queue_ping_raises(self, session_factory):
        """When queue.ping() raises, GET /health/ready returns 503."""
        class RaisingPingQueue:
            def enqueue(self, payload):
                pass

            def ping(self):
                raise RuntimeError("connection refused")

        app = create_app(
            storage=FakeObjectStorage(),
            queue=RaisingPingQueue(),
            session_factory=session_factory,
        )
        client = TestClient(app)
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data.get("status") == "not_ready"
        assert data.get("checks", {}).get("redis") == "unavailable"
