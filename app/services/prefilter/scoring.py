"""Combine feature components with weights and apply accept/gray/reject thresholds."""

from __future__ import annotations

from typing import Any

from app.core.constants import PrefilterDecision


def apply_weights(
    structural_components: dict[str, float],
    structural_weights: dict[str, float],
    exact_match_counts: dict[str, int],
    weight_exact: float,
    pattern_count: int,
    weight_pattern: float,
    context_boost: float,
    weight_context: float,
    lexical_score: float,
    weight_lexical: float,
) -> tuple[float, dict[str, float]]:
    """Compute weighted sum and feature breakdown for explainability."""
    breakdown: dict[str, float] = {}

    structural_sum = 0.0
    for key, value in structural_components.items():
        w = structural_weights.get(key, 0.0)
        structural_sum += w * value
    breakdown["structural"] = structural_sum

    exact_contribution = weight_exact * min(sum(exact_match_counts.values()), 5) / 5.0 if exact_match_counts else 0.0
    breakdown["exact_match"] = exact_contribution

    pattern_contribution = weight_pattern * min(pattern_count, 3) / 3.0 if pattern_count else 0.0
    breakdown["pattern"] = pattern_contribution

    breakdown["context_boost"] = weight_context * context_boost
    breakdown["lexical"] = weight_lexical * lexical_score

    total = (
        structural_sum
        + exact_contribution
        + pattern_contribution
        + weight_context * context_boost
        + weight_lexical * lexical_score
    )
    # Normalize to 0..1 if total weight sum could exceed 1
    total = max(0.0, min(1.0, total))
    return total, breakdown


def thresholds_to_decision(
    score: float,
    accept_threshold: float,
    gray_threshold: float,
) -> PrefilterDecision:
    """Map score to keep/gray/reject using configurable thresholds."""
    if score >= accept_threshold:
        return PrefilterDecision.KEEP
    if score >= gray_threshold:
        return PrefilterDecision.GRAY
    return PrefilterDecision.REJECT
