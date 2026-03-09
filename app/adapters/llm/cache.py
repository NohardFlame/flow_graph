"""Cache key strategy and in-memory cache for extraction results."""

from __future__ import annotations

from app.domain.extraction_models import ExtractionResult


def build_extraction_cache_key(
    model: str,
    prompt_version: str,
    schema_version: str,
    chunk_id: str,
    normalization_config_version: str = "",
) -> str:
    """Build a deterministic cache key for an extraction request.

    Key components (per spec): model, prompt_version, schema_version,
    chunk hash (we use chunk_id as it is already deterministic), and
    normalization config version.
    """
    parts = [
        model,
        prompt_version,
        schema_version,
        chunk_id,
        normalization_config_version or "",
    ]
    return "|".join(parts)


class InMemoryExtractionCache:
    """In-memory cache for ExtractionResult. Cache hit returns result with cache_hit=True."""

    def __init__(self) -> None:
        self._store: dict[str, ExtractionResult] = {}

    def get(self, key: str) -> ExtractionResult | None:
        """Return cached result if present. Caller should set cache_hit=True when returning to consumer."""
        return self._store.get(key)

    def set(self, key: str, result: ExtractionResult) -> None:
        """Store result under key. Store with cache_hit=False (actual hit is signaled when returning from get)."""
        self._store[key] = result

    def __len__(self) -> int:
        return len(self._store)


def with_cache_hit(result: ExtractionResult) -> ExtractionResult:
    """Return a copy of result with cache_hit=True. Use when returning a cached result."""
    return ExtractionResult(
        drafts=result.drafts,
        provider=result.provider,
        model=result.model,
        prompt_version=result.prompt_version,
        schema_version=result.schema_version,
        cache_hit=True,
        retry_count=result.retry_count,
        latency_ms=result.latency_ms,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        estimated_cost_usd=result.estimated_cost_usd,
        warnings=result.warnings,
        fallback_used=result.fallback_used,
        raw_response=result.raw_response,
        repaired_response=result.repaired_response,
    )
