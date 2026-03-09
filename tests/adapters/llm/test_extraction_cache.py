"""Cache key and in-memory cache: key includes versions; hit returns cache_hit=True."""

from app.adapters.llm.cache import (
    InMemoryExtractionCache,
    build_extraction_cache_key,
    with_cache_hit,
)
from app.domain.extraction_models import ExtractionResult
from app.domain.normalization_models import ExtractionDraft


def _result(cache_hit: bool = False) -> ExtractionResult:
    return ExtractionResult(
        drafts=(ExtractionDraft(verb="submit"),),
        provider="p",
        model="m",
        prompt_version="v1",
        schema_version="v1",
        cache_hit=cache_hit,
        retry_count=0,
        latency_ms=100,
        input_tokens=10,
        output_tokens=5,
        estimated_cost_usd=0.001,
        warnings=(),
    )


class TestBuildExtractionCacheKey:
    def test_deterministic_same_inputs(self):
        a = build_extraction_cache_key("gpt-4", "v1", "v1", "chunk-abc", "norm1")
        b = build_extraction_cache_key("gpt-4", "v1", "v1", "chunk-abc", "norm1")
        assert a == b

    def test_includes_model_prompt_schema_chunk_norm(self):
        key = build_extraction_cache_key("gpt-4o", "p2", "s2", "chunk-xyz", "norm-v2")
        assert "gpt-4o" in key
        assert "p2" in key
        assert "s2" in key
        assert "chunk-xyz" in key
        assert "norm-v2" in key

    def test_different_chunk_different_key(self):
        k1 = build_extraction_cache_key("m", "v1", "v1", "c1", "")
        k2 = build_extraction_cache_key("m", "v1", "v1", "c2", "")
        assert k1 != k2


class TestInMemoryExtractionCache:
    def test_miss_returns_none(self):
        cache = InMemoryExtractionCache()
        assert cache.get("missing") is None

    def test_set_then_get_returns_same_result(self):
        cache = InMemoryExtractionCache()
        r = _result()
        cache.set("k1", r)
        got = cache.get("k1")
        assert got is not None
        assert got.drafts == r.drafts
        assert got.model == r.model

    def test_cache_hit_flag_exposed_via_with_cache_hit(self):
        r = _result(cache_hit=False)
        r2 = with_cache_hit(r)
        assert r2.cache_hit is True
        assert r.cache_hit is False
        assert r2.drafts == r.drafts
