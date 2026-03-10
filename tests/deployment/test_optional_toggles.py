"""Optional feature toggles: Qdrant disabled path, debug artifact mode.

Verifies that disabled optional modules do not require their config and that
debug artifact mode can be enabled without breaking startup.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.queue.fake_queue import FakeJobQueue
from app.adapters.storage.fake_storage import FakeObjectStorage
from app.api.app import create_app
from app.config.settings import get_settings, reset_settings_cache
from app.db.session import get_session_factory

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestQdrantDisabledPath:
    """With Qdrant disabled (default), app and worker start without Qdrant config."""

    def test_default_settings_has_qdrant_disabled(self):
        """Default settings have enable_qdrant False; no Qdrant client required."""
        settings = get_settings()
        assert settings.enable_qdrant is False
        assert settings.qdrant.enabled is False

    def test_api_starts_with_qdrant_disabled(self, subprocess_env_minimal_valid):
        """API process can start with ENABLE_QDRANT unset (Qdrant disabled)."""
        env = subprocess_env_minimal_valid.copy()
        env.pop("ENABLE_QDRANT", None)
        env["USE_FAKE_ADAPTERS"] = "1"
        result = subprocess.run(
            [sys.executable, "-c", "from app.api.main import app; print(app.title)"],
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
            env=env,
            timeout=10,
        )
        assert result.returncode == 0, (result.stdout, result.stderr)
        assert "flow-graph" in result.stdout

    def test_health_live_responds_when_qdrant_disabled(self):
        """With default (Qdrant disabled), health/live returns 200."""
        app = create_app(
            storage=FakeObjectStorage(),
            queue=FakeJobQueue(),
            session_factory=get_session_factory(),
        )
        client = TestClient(app)
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json().get("status") == "ok"


class TestDebugArtifactMode:
    """When OBS_ENABLE_DEBUG_ARTIFACTS is enabled, pipeline does not crash."""

    def test_settings_load_with_debug_artifacts_enabled(self, monkeypatch, settings_factory_uncached):
        """Settings load successfully with OBS_ENABLE_DEBUG_ARTIFACTS=true."""
        reset_settings_cache()
        monkeypatch.setenv("OBS_ENABLE_DEBUG_ARTIFACTS", "true")
        settings = get_settings()
        assert settings.observability.enable_debug_artifacts is True

    def test_app_creates_and_health_responds_with_debug_artifacts_enabled(self, monkeypatch, settings_factory_uncached):
        """With debug artifacts enabled, app creates and health/live responds."""
        reset_settings_cache()
        monkeypatch.setenv("OBS_ENABLE_DEBUG_ARTIFACTS", "1")
        app = create_app(
            storage=FakeObjectStorage(),
            queue=FakeJobQueue(),
            session_factory=get_session_factory(),
        )
        client = TestClient(app)
        response = client.get("/health/live")
        assert response.status_code == 200
        assert response.json().get("status") == "ok"
