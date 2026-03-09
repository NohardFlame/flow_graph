"""Integration-style flow: cache + adapter (fake), success/retry/repair/cache paths.

Tests do not mask failures: validation errors and exceptions are asserted
so schema or parser regressions are visible.
"""

import pytest

from app.adapters.llm.cache import (
    build_extraction_cache_key,
    with_cache_hit,
    InMemoryExtractionCache,
)
from app.adapters.llm.fake_llm_adapter import FakeLLMAdapter
from app.adapters.llm.retry_repair import extract_with_retry
from app.core.errors import RetryableExternalError, ValidationError
from app.domain.parse_models import ExtractionChunk


def _chunk(chunk_id: str = "c1") -> ExtractionChunk:
    return ExtractionChunk(
        chunk_id=chunk_id,
        section_path=["1"],
        chunk_text="User submits form.",
        source_spans={},
        page_refs=[],
        estimated_tokens=10,
    )


def _prompt_cfg() -> dict:
    return {"prompt_version": "v1", "schema_version": "v1"}


def extract_with_cache(
    adapter: FakeLLMAdapter,
    cache: InMemoryExtractionCache,
    chunk: ExtractionChunk,
    prompt_cfg: dict,
    model: str = "fake",
    normalization_version: str = "",
):
    """Simulate gateway: check cache, on miss call adapter, store and return; on hit return with_cache_hit."""
    key = build_extraction_cache_key(
        model=model,
        prompt_version=prompt_cfg.get("prompt_version", "v1"),
        schema_version=prompt_cfg.get("schema_version", "v1"),
        chunk_id=chunk.chunk_id,
        normalization_config_version=normalization_version,
    )
    cached = cache.get(key)
    if cached is not None:
        return with_cache_hit(cached)
    result = adapter.extract_actions(chunk, prompt_cfg)
    cache.set(key, result)
    return result


class TestExtractionFlowSuccess:
    def test_success_path_returns_drafts_and_metadata(self):
        adapter = FakeLLMAdapter(extraction_responses=['[{"verb": "submit", "primary_object": "form"}]'])
        cache = InMemoryExtractionCache()
        result = extract_with_cache(adapter, cache, _chunk(), _prompt_cfg())
        assert len(result.drafts) == 1
        assert result.drafts[0].verb == "submit"
        assert result.model == "fake"
        assert result.cache_hit is False

    def test_retry_then_success(self):
        adapter = FakeLLMAdapter(
            extraction_responses=[
                RetryableExternalError("timeout"),
                '[{"verb": "open"}]',
            ]
        )
        result = extract_with_retry(adapter, _chunk(), _prompt_cfg(), max_retries=2)
        assert len(result.drafts) == 1
        assert result.drafts[0].verb == "open"


class TestExtractionFlowCache:
    def test_identical_request_uses_cache_second_time(self):
        adapter = FakeLLMAdapter(
            extraction_responses=[
                '[{"verb": "first"}]',
                '[{"verb": "second"}]',
            ]
        )
        cache = InMemoryExtractionCache()
        r1 = extract_with_cache(adapter, cache, _chunk(), _prompt_cfg())
        r2 = extract_with_cache(adapter, cache, _chunk(), _prompt_cfg())
        assert r1.cache_hit is False
        assert r2.cache_hit is True
        assert r2.drafts == r1.drafts
        assert adapter.extract_call_count == 1

    def test_different_chunk_id_different_cache_key(self):
        adapter = FakeLLMAdapter(
            extraction_responses=[
                '[{"verb": "a"}]',
                '[{"verb": "b"}]',
            ]
        )
        cache = InMemoryExtractionCache()
        r1 = extract_with_cache(adapter, cache, _chunk("c1"), _prompt_cfg())
        r2 = extract_with_cache(adapter, cache, _chunk("c2"), _prompt_cfg())
        assert r1.drafts[0].verb == "a"
        assert r2.drafts[0].verb == "b"
        assert adapter.extract_call_count == 2


class TestExtractionFlowValidationNotMasked:
    def test_invalid_json_raises_validation_error(self):
        adapter = FakeLLMAdapter(extraction_responses=["not json at all"])
        with pytest.raises(ValidationError):
            adapter.extract_actions(_chunk(), _prompt_cfg())
