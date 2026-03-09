"""Scoring: weights and thresholds."""

import pytest

from app.core.constants import PrefilterDecision
from app.services.prefilter.scoring import apply_weights, thresholds_to_decision


def test_thresholds_to_decision_keep():
    assert thresholds_to_decision(0.6, 0.5, 0.3) == PrefilterDecision.KEEP
    assert thresholds_to_decision(0.5, 0.5, 0.3) == PrefilterDecision.KEEP


def test_thresholds_to_decision_gray():
    assert thresholds_to_decision(0.4, 0.5, 0.3) == PrefilterDecision.GRAY
    assert thresholds_to_decision(0.3, 0.5, 0.3) == PrefilterDecision.GRAY


def test_thresholds_to_decision_reject():
    assert thresholds_to_decision(0.2, 0.5, 0.3) == PrefilterDecision.REJECT
    assert thresholds_to_decision(0.0, 0.5, 0.3) == PrefilterDecision.REJECT


def test_apply_weights_combines_deterministically():
    structural = {"heading_relevant": 1.0, "has_table_list": 0.0, "depth_score": 0.2, "appendix_penalty": 0.0}
    struct_weights = {"heading_relevant": 0.2, "has_table_list": 0.1, "depth_score": 0.1, "appendix_penalty": -0.2}
    total, breakdown = apply_weights(
        structural,
        struct_weights,
        {"action_verbs": 1},
        0.25,
        1,
        0.2,
        0.5,
        0.15,
        0.3,
        0.1,
    )
    assert "structural" in breakdown
    assert "exact_match" in breakdown
    assert "pattern" in breakdown
    assert "context_boost" in breakdown
    assert "lexical" in breakdown
    assert 0 <= total <= 1.0


def test_turning_off_feature_family_changes_score():
    structural = {"heading_relevant": 1.0, "has_table_list": 0.0, "depth_score": 0.0, "appendix_penalty": 0.0}
    struct_weights = {"heading_relevant": 0.2, "has_table_list": 0.0, "depth_score": 0.0, "appendix_penalty": 0.0}
    total_with, _ = apply_weights(
        structural, struct_weights, {}, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0,
    )
    struct_weights_off = {"heading_relevant": 0.0, "has_table_list": 0.0, "depth_score": 0.0, "appendix_penalty": 0.0}
    total_without, _ = apply_weights(
        structural, struct_weights_off, {}, 0.0, 0, 0.0, 0.0, 0.0, 0.0, 0.0,
    )
    assert total_with > total_without
