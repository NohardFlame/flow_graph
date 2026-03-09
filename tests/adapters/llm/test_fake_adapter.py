"""Fake LLM adapter: success, error sequence, repair sequence."""

import pytest

from app.adapters.llm.fake_llm_adapter import FakeLLMAdapter
from app.core.errors import PermanentExternalError, RetryableExternalError, ValidationError
from app.domain.extraction_models import RepairResult
from app.domain.normalization_models import ExtractionDraft
from app.domain.parse_models import ExtractionChunk


def _chunk() -> ExtractionChunk:
    return ExtractionChunk(
        chunk_id="c1",
        section_path=["1"],
        chunk_text="User submits form.",
        source_spans={},
        page_refs=[],
        estimated_tokens=10,
    )


def _prompt_cfg() -> dict:
    return {"prompt_version": "v1", "schema_version": "v1"}


class TestFakeAdapterSuccess:
    def test_returns_parsed_drafts(self):
        adapter = FakeLLMAdapter(extraction_responses=['[{"verb": "submit", "primary_object": "form"}]'])
        result = adapter.extract_actions(_chunk(), _prompt_cfg())
        assert len(result.drafts) == 1
        assert result.drafts[0].verb == "submit"
        assert result.drafts[0].primary_object == "form"
        assert result.provider == "fake"
        assert result.cache_hit is False

    def test_uses_prompt_cfg_versions(self):
        adapter = FakeLLMAdapter(extraction_responses=["[]"])
        result = adapter.extract_actions(_chunk(), {"prompt_version": "v2", "schema_version": "v2"})
        assert result.prompt_version == "v2"
        assert result.schema_version == "v2"


class TestFakeAdapterSequence:
    def test_first_call_raises_then_second_succeeds(self):
        adapter = FakeLLMAdapter(
            extraction_responses=[
                RetryableExternalError("timeout"),
                '[{"verb": "open"}]',
            ]
        )
        with pytest.raises(RetryableExternalError):
            adapter.extract_actions(_chunk(), _prompt_cfg())
        result = adapter.extract_actions(_chunk(), _prompt_cfg())
        assert len(result.drafts) == 1
        assert result.drafts[0].verb == "open"

    def test_permanent_error_raised_as_is(self):
        adapter = FakeLLMAdapter(extraction_responses=[PermanentExternalError("auth failed")])
        with pytest.raises(PermanentExternalError) as exc_info:
            adapter.extract_actions(_chunk(), _prompt_cfg())
        assert "auth" in str(exc_info.value).lower()


class TestFakeAdapterInvalidJson:
    def test_invalid_json_raises_validation_error(self):
        adapter = FakeLLMAdapter(extraction_responses=["not json"])
        with pytest.raises(ValidationError):
            adapter.extract_actions(_chunk(), _prompt_cfg())


class TestFakeAdapterRepair:
    def test_repair_json_returns_configured_result(self):
        draft = ExtractionDraft(verb="submit", primary_object="form")
        adapter = FakeLLMAdapter(
            repair_responses=[
                RepairResult(repaired_json='[{"verb":"submit","primary_object":"form"}]', success=True, drafts=(draft,)),
            ]
        )
        result = adapter.repair_json("bad json", "v1")
        assert result.success is True
        assert result.drafts is not None
        assert len(result.drafts) == 1
        assert result.drafts[0].verb == "submit"

    def test_repair_empty_queue_returns_failure(self):
        adapter = FakeLLMAdapter(repair_responses=[])
        result = adapter.repair_json("bad", "v1")
        assert result.success is False
        assert result.drafts is None
