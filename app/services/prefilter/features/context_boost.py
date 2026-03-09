"""Context boosts when multiple signal types co-occur near each other."""

from __future__ import annotations

import re


def _tokenize_for_window(text: str) -> list[str]:
    """Simple tokenization: lowercase words (alphanumeric)."""
    return re.findall(r"[a-z0-9]+", text.lower())


def context_boost_score(
    text: str,
    *,
    action_terms: list[str],
    object_terms: list[str],
    modal_restriction_terms: list[str],
    role_terms: list[str],
    state_terms: list[str],
    window_size: int = 10,
) -> float:
    """Score 0..1 for co-occurrence of signal types within a token window.

    Boosts: action near object; modal/restriction near role; state near object.
    """
    if not text:
        return 0.0
    tokens = _tokenize_for_window(text)
    if not tokens:
        return 0.0

    action_set = set(action_terms) if action_terms else set()
    object_set = set(object_terms) if object_terms else set()
    modal_set = set(modal_restriction_terms) if modal_restriction_terms else set()
    role_set = set(role_terms) if role_terms else set()
    state_set = set(state_terms) if state_terms else set()

    boosts = 0.0
    n_windows = 0
    for i in range(len(tokens) - 1):
        end = min(i + window_size, len(tokens))
        window = set(tokens[i:end])
        n_windows += 1
        if action_set and object_set and (window & action_set) and (window & object_set):
            boosts += 1.0
        if modal_set and role_set and (window & modal_set) and (window & role_set):
            boosts += 1.0
        if state_set and object_set and (window & state_set) and (window & object_set):
            boosts += 1.0

    if n_windows == 0:
        return 0.0
    # Cap at 1.0
    raw = boosts / n_windows
    return min(raw * 3.0, 1.0)  # scale so a few hits can reach 1.0
