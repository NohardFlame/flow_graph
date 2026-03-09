"""Shared fixtures for Phase 0 and beyond.

Use monkeypatch for env; avoid patching Pydantic or internal helpers.
Do not share mutated settings across tests.
"""

import pytest

from app.config.settings import reset_settings_cache


@pytest.fixture
def settings_factory_uncached():
    """Reset settings cache so the next get_settings() loads fresh from env."""
    reset_settings_cache()
    yield
    reset_settings_cache()


@pytest.fixture
def env_minimal_valid(monkeypatch):
    """Set minimal env vars so get_settings() succeeds (no real cloud credentials)."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    yield
    reset_settings_cache()


@pytest.fixture
def env_missing_required_var(monkeypatch):
    """Unset required env var so get_settings() raises."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    yield
    reset_settings_cache()


@pytest.fixture
def env_invalid_port(monkeypatch):
    """Set API port to invalid value so validation fails."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("API_PORT", "not_a_number")
    yield
    reset_settings_cache()
