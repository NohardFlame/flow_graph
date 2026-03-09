"""Prefilter service integration: score_chunks with fixtures."""

import pytest
from pathlib import Path

from app.config.settings import PrefilterSettings
from app.services.prefilter.features.patterns import FakePatternMatcher
from app.services.prefilter.service import PrefilterService
from tests.fixtures.prefilter_fixtures import (
    fixture_explicit_action,
    fixture_glossary_noise,
    fixture_permission,
    fixture_restriction,
)


def _lexicon_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "prefilter"


@pytest.fixture
def prefilter_service():
    if not _lexicon_dir().is_dir():
        pytest.skip("data/prefilter not found")
    settings = PrefilterSettings(
        lexicon_dir=str(_lexicon_dir()),
        enable_pattern_matching=False,
    )
    return PrefilterService(
        settings=settings,
        lexicon_dir=_lexicon_dir(),
        pattern_matcher=FakePatternMatcher([]),
    )


def test_score_chunks_returns_one_result_per_chunk(prefilter_service):
    chunks = [fixture_explicit_action(), fixture_glossary_noise()]
    results = prefilter_service.score_chunks(chunks)
    assert len(results) == 2
    for r in results:
        assert 0 <= r.prefilter_score <= 1.0
        assert r.decision.value in ("keep", "gray", "reject")
        assert "structural" in r.feature_breakdown
        assert isinstance(r.matched_terms, list)
        assert isinstance(r.structural_flags, dict)


def test_score_chunks_action_chunk_scores_higher_than_glossary(prefilter_service):
    action = fixture_explicit_action()
    glossary = fixture_glossary_noise()
    results = prefilter_service.score_chunks([action, glossary])
    assert results[0].prefilter_score > results[1].prefilter_score


def test_score_chunks_permission_and_restriction_get_matches(prefilter_service):
    chunks = [fixture_permission(), fixture_restriction()]
    results = prefilter_service.score_chunks(chunks)
    assert len(results[0].matched_terms) >= 1
    assert len(results[1].matched_terms) >= 1


def test_score_chunks_empty_list(prefilter_service):
    assert prefilter_service.score_chunks([]) == []


def test_score_chunks_apply_gray_policy(prefilter_service):
    chunks = [fixture_explicit_action(), fixture_glossary_noise(), fixture_permission()]
    with_policy = prefilter_service.score_chunks(chunks, apply_gray_policy_flag=True)
    without_policy = prefilter_service.score_chunks(chunks, apply_gray_policy_flag=False)
    assert len(with_policy) == len(without_policy)
    # With policy, some gray may have selected_for_llm False
    assert any(hasattr(r, "selected_for_llm") for r in with_policy)
