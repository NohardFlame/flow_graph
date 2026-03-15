"""Context boosts when multiple signal types co-occur near each other."""

from __future__ import annotations

import re

# ASCII alphanumeric + Cyrillic (U+0400–U+04FF) for Russian and similar scripts
_TOKEN_PATTERN = re.compile(r"[a-z0-9\u0400-\u04ff]+", re.IGNORECASE)


def _tokenize_for_window(text: str) -> list[str]:
    """Tokenization: lowercase words (ASCII + Cyrillic alphanumeric)."""
    return [m.lower() for m in _TOKEN_PATTERN.findall(text)]


def _window_has_term_match(window_tokens: list[str], terms: list[str]) -> bool:
    """True if any token in window contains any term as substring (stem-in-word or exact)."""
    if not terms:
        return False
    window_set = set(window_tokens)
    for t in window_set:
        for p in terms:
            if p in t:
                return True
    return False


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
    Terms can be full words (e.g. may) or stems (e.g. разреш); matching is substring (stem-in-word).
    """
    if not text:
        return 0.0
    tokens = _tokenize_for_window(text)
    if not tokens:
        return 0.0

    boosts = 0.0
    n_windows = 0
    for i in range(len(tokens) - 1):
        end = min(i + window_size, len(tokens))
        window = tokens[i:end]
        n_windows += 1
        if action_terms and object_terms and _window_has_term_match(window, action_terms) and _window_has_term_match(window, object_terms):
            boosts += 1.0
        if modal_restriction_terms and role_terms and _window_has_term_match(window, modal_restriction_terms) and _window_has_term_match(window, role_terms):
            boosts += 1.0
        if state_terms and object_terms and _window_has_term_match(window, state_terms) and _window_has_term_match(window, object_terms):
            boosts += 1.0

    if n_windows == 0:
        return 0.0
    # Cap at 1.0
    raw = boosts / n_windows
    return min(raw * 3.0, 1.0)  # scale so a few hits can reach 1.0
