"""Deterministic string-to-slug pipeline: trim, lower, punctuation, snake_case.

No alias application or reserved-word check here; those are applied by the service.
"""

import re


def slugify(raw: str) -> str:
    """Convert a name-like string to a deterministic snake_case slug.

    Steps: trim and normalize whitespace, lowercase, normalize punctuation and
    separators to single underscore, collapse multiple underscores, strip.
    Empty input returns empty string.
    """
    if not raw or not raw.strip():
        return ""
    s = " ".join(raw.split()).lower()
    # Replace separators and punctuation with underscore
    s = re.sub(r"[\s\-.,;:!/()]+", "_", s)
    # Remove any remaining non-alphanumeric except underscore
    s = re.sub(r"[^a-z0-9_]", "_", s)
    # Collapse multiple underscores
    s = re.sub(r"_+", "_", s)
    return s.strip("_")
