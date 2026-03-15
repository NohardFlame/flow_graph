"""Context window size for extraction batching. Config or model-based default."""

from app.config.settings import LiteLLMSettings

# Fallback context window (tokens) when LITELLM_CONTEXT_WINDOW is not set. Key = model name (lowercase).
MODEL_CONTEXT_WINDOW: dict[str, int] = {
    "gpt-4o-mini": 128_000,
    "gpt-4o": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
    "claude-3-5-sonnet": 200_000,
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
    "claude-3-haiku": 200_000,
    "gemini-3.1-flash-lite-preview": 1_000_000,
}


def get_effective_context_window(settings: LiteLLMSettings) -> int:
    """Return context window size in tokens. Uses config or model-based default."""
    if settings.context_window and settings.context_window > 0:
        return settings.context_window
    model = (settings.model or "").strip().lower()
    return MODEL_CONTEXT_WINDOW.get(model, 128_000)


def get_max_input_tokens(settings: LiteLLMSettings) -> int:
    """Return max input tokens (e.g. 70% of context window) for extraction batching."""
    window = get_effective_context_window(settings)
    ratio = max(0.0, min(1.0, settings.context_window_fill_ratio))
    return int(window * ratio)
