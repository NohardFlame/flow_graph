"""Tests for configuration loading: deterministic, validated, override-friendly."""

import pytest

from app.config.settings import get_settings, reset_settings_cache
from app.core.errors import ConfigError


class TestSettingsLoading:
    """Settings loading from environment."""

    def test_loads_valid_settings_from_environment(self, env_minimal_valid):
        settings = get_settings()
        assert settings.environment == "test"

    def test_applies_defaults_when_optional_values_omitted(self, env_minimal_valid):
        settings = get_settings()
        assert settings.api.port == 8000
        assert settings.api.host == "0.0.0.0"
        assert settings.postgres.host == "localhost"
        assert settings.postgres.port == 5432

    def test_raises_on_missing_required_values(
        self, env_missing_required_var, settings_factory_uncached
    ):
        reset_settings_cache()
        with pytest.raises(ConfigError):
            get_settings()

    def test_raises_on_invalid_types(
        self, env_invalid_port, settings_factory_uncached
    ):
        reset_settings_cache()
        with pytest.raises(ConfigError):
            get_settings()

    def test_respects_feature_flags(self, env_minimal_valid, monkeypatch):
        reset_settings_cache()
        monkeypatch.setenv("USE_FAKE_ADAPTERS", "1")
        monkeypatch.setenv("ENABLE_QDRANT", "true")
        monkeypatch.setenv("ENABLE_LLM_CACHE", "1")
        monkeypatch.setenv("ENABLE_PREFILTER_DEBUG_FIELDS", "yes")
        settings = get_settings()
        assert settings.use_fake_adapters is True
        assert settings.enable_qdrant is True
        assert settings.enable_llm_cache is True
        assert settings.enable_prefilter_debug_fields is True


class TestCaching:
    """Settings factory cache behavior."""

    def test_repeated_factory_calls_return_same_object_when_caching_enabled(
        self, env_minimal_valid, settings_factory_uncached
    ):
        a = get_settings()
        b = get_settings()
        assert a is b

    def test_cache_reset_creates_fresh_object(
        self, env_minimal_valid, settings_factory_uncached
    ):
        a = get_settings()
        reset_settings_cache()
        b = get_settings()
        assert a is not b
        assert a.environment == b.environment


class TestErrorTranslation:
    """Invalid settings map to internal ConfigError."""

    def test_invalid_settings_map_to_config_error(
        self, env_invalid_port, settings_factory_uncached
    ):
        reset_settings_cache()
        with pytest.raises(ConfigError) as exc_info:
            get_settings()
        assert "Invalid configuration" in str(exc_info.value)
