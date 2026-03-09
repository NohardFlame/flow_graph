"""Exact and alias phrase matching against chunk text."""

from __future__ import annotations


def normalize_text(text: str) -> str:
    """Lowercase and collapse whitespace for matching."""
    return " ".join(text.lower().split())


def find_matches(
    text: str,
    lexicons_by_category: dict[str, list[str]],
    *,
    normalize: bool = True,
) -> tuple[list[str], dict[str, int]]:
    """Find all lexicon phrase matches in text.

    Args:
        text: Chunk text (and optionally section path concatenation).
        lexicons_by_category: Category name -> list of normalized phrases.
        normalize: Whether to normalize text before matching.

    Returns:
        (matched_terms, counts_by_category). Each matched term appears once;
        counts_by_category is how many distinct phrases matched per category.
    """
    if normalize:
        text = normalize_text(text)
    matched: set[str] = set()
    counts: dict[str, int] = {}

    for category, phrases in lexicons_by_category.items():
        n = 0
        for phrase in phrases:
            if not phrase:
                continue
            if phrase in text and phrase not in matched:
                matched.add(phrase)
                n += 1
        if n > 0:
            counts[category] = n

    return list(matched), counts
