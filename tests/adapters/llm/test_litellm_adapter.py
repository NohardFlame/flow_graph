"""LiteLLM adapter: exception mapping and flow with mocked completion (no live API)."""

from unittest.mock import MagicMock, patch

import pytest

from app.adapters.llm.litellm_adapter import LiteLLMAdapter
from app.config.settings import LiteLLMSettings
from app.core.errors import ExtractionError, PermanentExternalError, RetryableExternalError
from app.domain.parse_models import ExtractionChunk


def _chunk() -> ExtractionChunk:
    return ExtractionChunk(
        chunk_id="c1",
        section_path=["1"],
        chunk_text="User submits the form.",
        source_spans={},
        page_refs=[],
        estimated_tokens=10,
    )


def _prompt_cfg() -> dict:
    return {"prompt_version": "v1", "schema_version": "v1"}


def _mock_response(content: str, model: str = "gpt-4o-mini", prompt_tokens: int = 5, completion_tokens: int = 10):
    choice = MagicMock()
    choice.message.content = content
    choice.message.role = "assistant"
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    resp = MagicMock()
    resp.choices = [choice]
    resp.model = model
    resp.usage = usage
    return resp


@patch("litellm.completion")
class TestLiteLLMAdapterExtractActions:
    def test_valid_response_returns_extraction_result(self, mock_completion):
        mock_completion.return_value = _mock_response('[{"verb": "submit", "primary_object": "form"}]')
        settings = LiteLLMSettings(model="gpt-4o-mini", max_retries=0)
        adapter = LiteLLMAdapter(settings)
        result = adapter.extract_actions(_chunk(), _prompt_cfg())
        assert len(result.drafts) == 1
        assert result.drafts[0].verb == "submit"
        assert result.drafts[0].primary_object == "form"
        assert result.provider == "litellm"
        assert result.cache_hit is False
        assert result.input_tokens == 5
        assert result.output_tokens == 10

    def test_invalid_json_raises_extraction_error(self, mock_completion):
        mock_completion.return_value = _mock_response("not json")
        settings = LiteLLMSettings(model="gpt-4o-mini", max_retries=0, repair_max_attempts=0)
        adapter = LiteLLMAdapter(settings)
        with pytest.raises(ExtractionError):
            adapter.extract_actions(_chunk(), _prompt_cfg())

    def test_repair_json_returns_repair_result(self, mock_completion):
        mock_completion.return_value = _mock_response('[{"verb": "fix"}]')
        settings = LiteLLMSettings(model="gpt-4o-mini")
        adapter = LiteLLMAdapter(settings)
        result = adapter.repair_json("bad { json", {"schema_version": "v1"})
        assert result.success is True
        assert result.drafts is not None
        assert len(result.drafts) == 1
        assert result.drafts[0].verb == "fix"
