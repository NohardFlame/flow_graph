"""Retry and repair policy: transient retries up to cap, permanent stops immediately."""

import pytest

from app.adapters.llm.fake_llm_adapter import FakeLLMAdapter
from app.adapters.llm.retry_repair import extract_with_retry, is_retryable
from app.core.errors import PermanentExternalError, RetryableExternalError
from app.domain.parse_models import ExtractionChunk


def _chunk() -> ExtractionChunk:
    return ExtractionChunk(
        chunk_id="c1",
        section_path=[],
        chunk_text="text",
        source_spans={},
        page_refs=[],
        estimated_tokens=5,
    )


def _prompt_cfg() -> dict:
    return {"prompt_version": "v1", "schema_version": "v1"}


class TestIsRetryable:
    def test_retryable_external_error_is_retryable(self):
        assert is_retryable(RetryableExternalError("timeout")) is True

    def test_permanent_external_error_not_retryable(self):
        assert is_retryable(PermanentExternalError("auth failed")) is False


class TestExtractWithRetry:
    def test_success_first_call_no_retry(self):
        adapter = FakeLLMAdapter(extraction_responses=['[{"verb": "submit"}]'])
        result = extract_with_retry(adapter, _chunk(), _prompt_cfg(), max_retries=2)
        assert len(result.drafts) == 1
        assert adapter.extract_call_count == 1

    def test_transient_then_success_retries_up_to_cap(self):
        adapter = FakeLLMAdapter(
            extraction_responses=[
                RetryableExternalError("timeout"),
                RetryableExternalError("rate limit"),
                '[{"verb": "open"}]',
            ]
        )
        result = extract_with_retry(adapter, _chunk(), _prompt_cfg(), max_retries=2)
        assert len(result.drafts) == 1
        assert result.drafts[0].verb == "open"
        assert adapter.extract_call_count == 3

    def test_permanent_error_stops_immediately(self):
        adapter = FakeLLMAdapter(extraction_responses=[PermanentExternalError("auth failed")])
        with pytest.raises(PermanentExternalError):
            extract_with_retry(adapter, _chunk(), _prompt_cfg(), max_retries=2)
        assert adapter.extract_call_count == 1

    def test_all_retries_exhausted_raises_last_error(self):
        adapter = FakeLLMAdapter(
            extraction_responses=[
                RetryableExternalError("e1"),
                RetryableExternalError("e2"),
                RetryableExternalError("e3"),
            ]
        )
        with pytest.raises(RetryableExternalError):
            extract_with_retry(adapter, _chunk(), _prompt_cfg(), max_retries=2)
        assert adapter.extract_call_count == 3
