"""Metrics protocol and implementations for observability.

Use MetricsRecorder for run lifecycle, prefilter, LLM, and failure counters.
In-memory implementation for tests; no-op for production without a backend.
"""

from __future__ import annotations

from typing import Protocol


class MetricsRecorder(Protocol):
    """Protocol for recording observability metrics. Implementations may be no-op or collect."""

    def record_document_uploaded(self) -> None:
        """Record one document uploaded."""
        ...

    def record_run_started(self) -> None:
        """Record a run started."""
        ...

    def record_run_succeeded(self) -> None:
        """Record a run completed successfully."""
        ...

    def record_run_failed(self) -> None:
        """Record a run failed."""
        ...

    def record_run_partial(self) -> None:
        """Record a run completed with partial success (e.g. optional indexing failed)."""
        ...

    def record_prefilter_decisions(
        self,
        accept: int,
        gray: int,
        reject: int,
    ) -> None:
        """Record prefilter outcome counts for a run."""
        ...

    def record_llm_call(
        self,
        cache_hit: bool,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        estimated_cost: float | None = None,
    ) -> None:
        """Record one LLM extraction call."""
        ...

    def record_parse_failure(self) -> None:
        """Record a document parse failure."""
        ...

    def record_extraction_validation_failure(self) -> None:
        """Record an extraction/validation failure (e.g. invalid LLM output)."""
        ...

    def record_step_latency(self, step: str, elapsed_ms: int) -> None:
        """Record step execution latency in milliseconds."""
        ...


class NoOpMetricsRecorder:
    """Metrics recorder that does nothing. Use when no metrics backend is configured."""

    def record_document_uploaded(self) -> None:
        pass

    def record_run_started(self) -> None:
        pass

    def record_run_succeeded(self) -> None:
        pass

    def record_run_failed(self) -> None:
        pass

    def record_run_partial(self) -> None:
        pass

    def record_prefilter_decisions(self, accept: int, gray: int, reject: int) -> None:
        pass

    def record_llm_call(
        self,
        cache_hit: bool,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        estimated_cost: float | None = None,
    ) -> None:
        pass

    def record_parse_failure(self) -> None:
        pass

    def record_extraction_validation_failure(self) -> None:
        pass

    def record_step_latency(self, step: str, elapsed_ms: int) -> None:
        pass


class InMemoryMetricsRecorder:
    """In-memory metrics collector for tests. Holds counters and optional latency samples."""

    def __init__(self) -> None:
        self.documents_uploaded = 0
        self.run_started = 0
        self.run_succeeded = 0
        self.run_failed = 0
        self.run_partial = 0
        self.prefilter_accept = 0
        self.prefilter_gray = 0
        self.prefilter_reject = 0
        self.llm_calls = 0
        self.llm_cache_hits = 0
        self.parse_failures = 0
        self.extraction_validation_failures = 0
        self.step_latencies: list[tuple[str, int]] = []

    def record_document_uploaded(self) -> None:
        self.documents_uploaded += 1

    def record_run_started(self) -> None:
        self.run_started += 1

    def record_run_succeeded(self) -> None:
        self.run_succeeded += 1

    def record_run_failed(self) -> None:
        self.run_failed += 1

    def record_run_partial(self) -> None:
        self.run_partial += 1

    def record_prefilter_decisions(
        self,
        accept: int,
        gray: int,
        reject: int,
    ) -> None:
        self.prefilter_accept += accept
        self.prefilter_gray += gray
        self.prefilter_reject += reject

    def record_llm_call(
        self,
        cache_hit: bool,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        estimated_cost: float | None = None,
    ) -> None:
        self.llm_calls += 1
        if cache_hit:
            self.llm_cache_hits += 1

    def record_parse_failure(self) -> None:
        self.parse_failures += 1

    def record_extraction_validation_failure(self) -> None:
        self.extraction_validation_failures += 1

    def record_step_latency(self, step: str, elapsed_ms: int) -> None:
        self.step_latencies.append((step, elapsed_ms))
