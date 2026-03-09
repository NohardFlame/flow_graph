"""Gray-zone policy: top-N and adjacent-to-accepted."""

import pytest

from app.core.constants import PrefilterDecision
from app.services.prefilter.gray_zone import apply_gray_policy
from app.services.prefilter.prefilter_models import PrefilterResult


def _result(decision: PrefilterDecision, score: float = 0.0) -> PrefilterResult:
    return PrefilterResult(
        prefilter_score=score,
        decision=decision,
        feature_breakdown={},
        matched_terms=[],
        matched_patterns=[],
        structural_flags={},
        lexical_score=0.0,
        selected_for_llm=True,
    )


def test_keep_always_selected():
    results = [_result(PrefilterDecision.KEEP), _result(PrefilterDecision.GRAY)]
    out = apply_gray_policy(results, top_gray_budget=1, adjacent_to_accepted=False)
    assert out[0].selected_for_llm is True
    assert out[1].decision == PrefilterDecision.GRAY


def test_reject_never_selected():
    results = [_result(PrefilterDecision.REJECT)]
    out = apply_gray_policy(results, top_gray_budget=10, adjacent_to_accepted=True)
    assert out[0].selected_for_llm is False


def test_top_n_gray_selected():
    # Three grays with different scores; top 2 should be selected
    results = [
        _result(PrefilterDecision.GRAY, 0.4),
        _result(PrefilterDecision.GRAY, 0.35),
        _result(PrefilterDecision.GRAY, 0.45),
    ]
    out = apply_gray_policy(results, top_gray_budget=2, adjacent_to_accepted=False)
    selected = [r.selected_for_llm for r in out]
    assert sum(selected) == 2
    # Highest scores: 0.45 (idx 2), 0.4 (idx 0)
    assert out[2].selected_for_llm is True
    assert out[0].selected_for_llm is True
    assert out[1].selected_for_llm is False


def test_adjacent_to_accepted_selected():
    # KEEP at index 1; GRAY at 0 and 2 should be selected when adjacent_to_accepted=True
    results = [
        _result(PrefilterDecision.GRAY, 0.31),
        _result(PrefilterDecision.KEEP),
        _result(PrefilterDecision.GRAY, 0.32),
    ]
    out = apply_gray_policy(results, top_gray_budget=0, adjacent_to_accepted=True)
    assert out[0].selected_for_llm is True
    assert out[1].selected_for_llm is True
    assert out[2].selected_for_llm is True
