"""Token estimation for chunk text (approximate, for sizing and caps)."""

# Conservative: ~4 chars per token for English; use for soft caps
CHARS_PER_TOKEN_ESTIMATE = 4


def estimated_tokens(text: str) -> int:
    """Return estimated token count for text. Used for chunk size caps."""
    if not text or not text.strip():
        return 0
    return max(1, len(text.strip()) // CHARS_PER_TOKEN_ESTIMATE)
