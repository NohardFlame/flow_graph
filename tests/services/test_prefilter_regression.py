"""Regression: past misses and false positives as named fixtures."""

import pytest
from pathlib import Path

from app.config.settings import PrefilterSettings
from app.core.constants import PrefilterDecision
from app.services.prefilter.features.patterns import FakePatternMatcher
from app.services.prefilter.service import PrefilterService
from tests.fixtures.prefilter_fixtures import (
    fixture_explicit_action,
    fixture_false_positive_trap,
    fixture_glossary_noise,
    fixture_intro_noise,
    fixture_permission,
    fixture_restriction,
)


def _lexicon_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "prefilter"


@pytest.fixture
def service():
    if not _lexicon_dir().is_dir():
        pytest.skip("data/prefilter not found")
    settings = PrefilterSettings(lexicon_dir=str(_lexicon_dir()), enable_pattern_matching=False)
    return PrefilterService(
        settings=settings,
        lexicon_dir=_lexicon_dir(),
        pattern_matcher=FakePatternMatcher([]),
    )


def test_glossary_noise_low_score_or_reject(service):
    """Glossary should not be sent to LLM (reject or low score)."""
    results = service.score_chunks([fixture_glossary_noise()])
    r = results[0]
    assert r.decision in (PrefilterDecision.REJECT, PrefilterDecision.GRAY)
    assert r.prefilter_score < 0.6


def test_intro_noise_low_score_or_reject(service):
    """Introduction/overview should not dominate (reject or gray)."""
    results = service.score_chunks([fixture_intro_noise()])
    r = results[0]
    assert r.decision in (PrefilterDecision.REJECT, PrefilterDecision.GRAY)


def test_explicit_action_high_score_or_keep(service):
    """Chunk with explicit action language should be kept or high score."""
    results = service.score_chunks([fixture_explicit_action()])
    r = results[0]
    assert r.decision in (PrefilterDecision.KEEP, PrefilterDecision.GRAY)
    assert r.prefilter_score >= 0.2


def test_permission_chunk_detected(service):
    """Permission language should contribute to score (matched terms or high score)."""
    results = service.score_chunks([fixture_permission()])
    r = results[0]
    assert r.prefilter_score > 0.1 or len(r.matched_terms) >= 1


def test_false_positive_trap_lower_than_action(service):
    """Narrative with stray keyword should score lower than real action chunk."""
    action = fixture_explicit_action()
    trap = fixture_false_positive_trap()
    results = service.score_chunks([action, trap])
    assert results[0].prefilter_score >= results[1].prefilter_score
