"""Explainability: feature breakdown and diagnostics for rejected chunks."""

import pytest
from pathlib import Path

from app.config.settings import PrefilterSettings
from app.services.prefilter.features.patterns import FakePatternMatcher
from app.services.prefilter.service import PrefilterService
from tests.fixtures.prefilter_fixtures import fixture_glossary_noise, fixture_intro_noise


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


def test_feature_breakdown_contains_all_contributing_signals(service):
    chunk = fixture_glossary_noise()
    results = service.score_chunks([chunk])
    r = results[0]
    assert "structural" in r.feature_breakdown
    assert "exact_match" in r.feature_breakdown
    assert "pattern" in r.feature_breakdown
    assert "context_boost" in r.feature_breakdown
    assert "lexical" in r.feature_breakdown


def test_rejected_chunk_still_has_diagnostics(service):
    chunks = [fixture_glossary_noise(), fixture_intro_noise()]
    results = service.score_chunks(chunks)
    for r in results:
        assert r.feature_breakdown
        assert r.structural_flags
        assert "is_appendix_or_glossary_or_intro" in r.structural_flags
        assert isinstance(r.matched_terms, list)
        assert isinstance(r.matched_patterns, list)


def test_prefilter_result_to_dict_serializable(service):
    chunk = fixture_glossary_noise()
    results = service.score_chunks([chunk])
    d = results[0].to_dict()
    assert "prefilter_score" in d
    assert "decision" in d
    assert "feature_breakdown" in d
    assert "matched_terms" in d
    assert "structural_flags" in d
    assert "lexical_score" in d
    assert "selected_for_llm" in d
