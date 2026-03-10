"""Response parser: valid JSON -> drafts, invalid JSON/structure -> ValidationError.

Tests are meant to reveal bugs; we assert exact failure types and messages
so schema or parser regressions are caught.
"""

import pytest

from app.adapters.llm.response_parser import parse_extraction_response
from app.core.errors import ValidationError
from app.domain.normalization_models import ExtractionDraft


class TestParseExtractionResponseValid:
    def test_empty_array_returns_empty_list(self):
        result = parse_extraction_response("[]", "v1")
        assert result == []

    def test_single_action_maps_to_draft(self):
        raw = """[
            {"verb": "submit", "primary_object": "form", "primary_actor": "user"}
        ]"""
        result = parse_extraction_response(raw, "v1")
        assert len(result) == 1
        d = result[0]
        assert d.verb == "submit"
        assert d.primary_object == "form"
        assert d.primary_actor == "user"
        assert d.input_state is None
        assert d.output_state is None

    def test_all_fields_mapped(self):
        raw = """[{
            "verb": "approve",
            "primary_object": "request",
            "primary_actor": "admin",
            "input_state": "pending",
            "output_state": "approved",
            "action_label": "Approve request",
            "suggested_actor_canonical": "admin",
            "suggested_object_canonical": "request",
            "suggested_verb_canonical": "approve",
            "suggested_state_canonical": "approved"
        }]"""
        result = parse_extraction_response(raw, "v1")
        assert len(result) == 1
        d = result[0]
        assert d.verb == "approve"
        assert d.primary_object == "request"
        assert d.primary_actor == "admin"
        assert d.input_state == "pending"
        assert d.output_state == "approved"
        assert d.action_label == "Approve request"
        assert d.suggested_actor_canonical == "admin"
        assert d.suggested_object_canonical == "request"
        assert d.suggested_verb_canonical == "approve"
        assert d.suggested_state_canonical == "approved"

    def test_multiple_actions(self):
        raw = """[
            {"verb": "open", "primary_object": "file"},
            {"verb": "close", "primary_object": "file"}
        ]"""
        result = parse_extraction_response(raw, "v1")
        assert len(result) == 2
        assert result[0].verb == "open" and result[0].primary_object == "file"
        assert result[1].verb == "close" and result[1].primary_object == "file"

    def test_null_values_allowed(self):
        raw = """[{"verb": "do", "primary_object": null, "primary_actor": null}]"""
        result = parse_extraction_response(raw, "v1")
        assert len(result) == 1
        assert result[0].verb == "do"
        assert result[0].primary_object is None
        assert result[0].primary_actor is None

    def test_schema_version_1_1_parses_identically(self):
        """Structured output for action_draft_v1_1 parses same as v1 (parser contract unchanged)."""
        raw = '[{"verb": "create", "primary_object": "request", "action_label": "create request"}]'
        result_v1 = parse_extraction_response(raw, "v1")
        result_11 = parse_extraction_response(raw, "1.1")
        assert result_v1 == result_11
        assert len(result_11) == 1
        assert result_11[0].verb == "create"
        assert result_11[0].primary_object == "request"


class TestParseExtractionResponseInvalid:
    def test_empty_string_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            parse_extraction_response("", "v1")
        assert "empty" in exc_info.value.message.lower()

    def test_whitespace_only_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            parse_extraction_response("   \n  ", "v1")
        assert "empty" in exc_info.value.message.lower()

    def test_invalid_json_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            parse_extraction_response("not json at all", "v1")
        assert "not valid JSON" in exc_info.value.message

    def test_malformed_json_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            parse_extraction_response("[1, 2,", "v1")
        assert "JSON" in exc_info.value.message

    def test_non_array_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            parse_extraction_response('{"verb": "x"}', "v1")
        assert "array" in exc_info.value.message.lower()

    def test_array_item_not_object_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            parse_extraction_response('[ "string" ]', "v1")
        assert "index 0" in exc_info.value.message
        assert "object" in exc_info.value.message.lower()

    def test_unknown_key_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            parse_extraction_response('[{"verb": "x", "unknown_key": "y"}]', "v1")
        assert "unknown" in exc_info.value.message.lower() or "unknown_key" in exc_info.value.message

    def test_non_string_value_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            parse_extraction_response('[{"verb": 123}]', "v1")
        assert "string" in exc_info.value.message.lower() or "null" in exc_info.value.message
