"""Pattern matcher tests: fake and (optional) spaCy."""

import pytest

from app.services.prefilter.features.patterns import FakePatternMatcher, SpacyPatternMatcher


def test_fake_pattern_matcher_returns_configured():
    fake = FakePatternMatcher(["obligation_must_verb", "condition_if_when"])
    assert fake.match_patterns("any text") == ["obligation_must_verb", "condition_if_when"]


def test_fake_pattern_matcher_empty():
    fake = FakePatternMatcher([])
    assert fake.match_patterns("") == []


def test_spacy_pattern_matcher_fails_without_model(monkeypatch):
    """When spaCy model is missing, ConfigError is raised (mock loader to avoid spacy import in CI)."""
    from app.core.errors import ConfigError

    def fail_load(model_name):
        raise ConfigError(f"spaCy model '{model_name}' not found. Run: python -m spacy download {model_name}")

    monkeypatch.setattr("app.services.prefilter.features.patterns._ensure_spacy_model", fail_load)
    with pytest.raises(ConfigError) as exc_info:
        SpacyPatternMatcher("nonexistent_model_xyz_123")
    assert "spacy" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


def test_spacy_pattern_matcher_matches_obligation():
    """Run when en_core_web_sm is installed; skip otherwise."""
    from app.core.errors import ConfigError
    try:
        matcher = SpacyPatternMatcher("en_core_web_sm")
    except (ConfigError, OSError, ImportError):
        pytest.skip("en_core_web_sm not installed; run: python -m spacy download en_core_web_sm")
    patterns = matcher.match_patterns("The user must submit the form.")
    assert "obligation_must_verb" in patterns
