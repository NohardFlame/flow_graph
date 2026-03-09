"""Structural feature extraction from chunk metadata and section path."""

from __future__ import annotations

from typing import Any

from app.domain.parse_models import ExtractionChunk


# Section path segments that indicate low-relevance (appendix, glossary, intro)
NOISE_SECTION_KEYWORDS = {"appendix", "appendices", "glossary", "introduction", "overview", "table of contents"}


def structural_features(
    chunk: ExtractionChunk,
    heading_relevant_terms: list[str],
) -> tuple[dict[str, float], dict[str, bool | float]]:
    """Compute structural score components and flags for one chunk.

    Args:
        chunk: ExtractionChunk with section_path and structural_features.
        heading_relevant_terms: Normalized terms that make heading path relevant.

    Returns:
        (components, flags)
        - components: keys heading_relevant, has_table_list, depth_score, appendix_penalty
          (raw 0/1 or small floats for scorer to weight).
        - flags: heading_contains_relevant_term, has_table, has_list, section_depth,
          is_appendix_or_glossary_or_intro.
    """
    path = chunk.section_path or []
    path_lower = " ".join(path).lower()
    struct = chunk.structural_features or {}

    has_table = bool(struct.get("has_table", False))
    has_list = bool(struct.get("has_list", False))
    depth = int(struct.get("section_depth", 0))
    has_table_or_list = has_table or has_list

    heading_relevant = 0.0
    if heading_relevant_terms:
        for term in heading_relevant_terms:
            if term in path_lower:
                heading_relevant = 1.0
                break

    # Depth: cap at 5 levels, normalize to 0..1
    depth_score = min(depth / 5.0, 1.0) if depth else 0.0

    is_noise = False
    for kw in NOISE_SECTION_KEYWORDS:
        if kw in path_lower:
            is_noise = True
            break
    # Use 1.0 when noise so that weight_structural_appendix_penalty (negative) gives a penalty
    appendix_penalty = 1.0 if is_noise else 0.0

    components: dict[str, float] = {
        "heading_relevant": heading_relevant,
        "has_table_list": 1.0 if has_table_or_list else 0.0,
        "depth_score": depth_score,
        "appendix_penalty": appendix_penalty,
    }

    flags: dict[str, bool | float] = {
        "heading_contains_relevant_term": bool(heading_relevant),
        "has_table": has_table,
        "has_list": has_list,
        "section_depth": depth,
        "is_appendix_or_glossary_or_intro": is_noise,
    }

    return components, flags
