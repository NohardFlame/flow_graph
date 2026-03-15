"""Extraction gateway result types and metadata.

ExtractionResult carries validated drafts and usage/observability metadata.
RepairResult carries the outcome of a JSON repair attempt.
"""

from dataclasses import dataclass

from app.domain.normalization_models import ExtractionDraft


@dataclass(frozen=True)
class ExtractionResult:
    """Result of a single extraction call (or cache hit). Carries drafts and usage metadata."""

    drafts: tuple[ExtractionDraft, ...]
    provider: str
    model: str
    prompt_version: str
    schema_version: str
    cache_hit: bool
    retry_count: int
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost_usd: float | None
    warnings: tuple[str, ...]
    fallback_used: bool = False
    structured_output_used: bool = False
    schema_fallback_used: bool = False
    # Optional: for audit when repair was used (Phase 8 can persist)
    raw_response: str | None = None
    repaired_response: str | None = None
    # HTTP status code from provider when available (e.g. 200)
    status_code: int | None = None


@dataclass(frozen=True)
class RepairResult:
    """Outcome of a JSON repair attempt (fix invalid model output)."""

    repaired_json: str
    success: bool
    drafts: tuple[ExtractionDraft, ...] | None = None  # Parsed drafts if success
