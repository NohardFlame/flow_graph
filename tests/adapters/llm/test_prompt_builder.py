"""Prompt builder: includes chunk metadata, schema version, evidence; deterministic."""

from app.adapters.llm.prompt_builder import build_extraction_messages
from app.domain.parse_models import ExtractionChunk


def _make_chunk(
    chunk_id: str = "chunk-1",
    section_path: list[str] | None = None,
    chunk_text: str = "User submits the form.",
    estimated_tokens: int = 10,
) -> ExtractionChunk:
    return ExtractionChunk(
        chunk_id=chunk_id,
        section_path=section_path or ["1", "Introduction"],
        chunk_text=chunk_text,
        source_spans={},
        page_refs=[],
        estimated_tokens=estimated_tokens,
    )


class TestPromptBuilderContent:
    def test_includes_chunk_metadata(self):
        chunk = _make_chunk(chunk_id="abc123", section_path=["2", "Process"])
        messages = build_extraction_messages(chunk, "v1", "v1")
        user_content = messages[1]["content"]
        assert "abc123" in user_content
        assert "2" in user_content and "Process" in user_content
        assert "10" in user_content  # estimated_tokens

    def test_includes_schema_version(self):
        chunk = _make_chunk()
        messages = build_extraction_messages(chunk, "v1", "v2")
        system_content = messages[0]["content"]
        assert "v2" in system_content or "schema" in system_content.lower()

    def test_includes_evidence_instructions(self):
        chunk = _make_chunk()
        messages = build_extraction_messages(chunk, "v1", "v1")
        system_content = messages[0]["content"]
        assert "evidence" in system_content.lower() or "supported" in system_content.lower()
        assert "action" in system_content.lower()

    def test_includes_chunk_text_in_user_message(self):
        chunk = _make_chunk(chunk_text="Submit the request to the server.")
        messages = build_extraction_messages(chunk, "v1", "v1")
        user_content = messages[1]["content"]
        assert "Submit the request to the server." in user_content

    def test_includes_json_schema_guidance(self):
        chunk = _make_chunk()
        messages = build_extraction_messages(chunk, "v1", "v1")
        system_content = messages[0]["content"]
        assert "JSON" in system_content
        assert "verb" in system_content or "primary_object" in system_content

    def test_normalization_hint_included_when_provided(self):
        chunk = _make_chunk()
        messages = build_extraction_messages(
            chunk, "v1", "v1", normalization_hint="Use slug-style canonical forms."
        )
        system_content = messages[0]["content"]
        assert "slug-style" in system_content or "canonical" in system_content


class TestPromptBuilderDeterminism:
    def test_same_inputs_same_output(self):
        chunk = _make_chunk(chunk_id="id1", chunk_text="Same text.")
        a = build_extraction_messages(chunk, "v1", "v1")
        b = build_extraction_messages(chunk, "v1", "v1")
        assert a == b
        assert len(a) == 2
        assert a[0]["role"] == "system" and a[1]["role"] == "user"

    def test_different_chunk_different_output(self):
        c1 = _make_chunk(chunk_id="a", chunk_text="Text A")
        c2 = _make_chunk(chunk_id="b", chunk_text="Text B")
        a = build_extraction_messages(c1, "v1", "v1")
        b = build_extraction_messages(c2, "v1", "v1")
        assert a != b
        assert a[1]["content"] != b[1]["content"]

    def test_different_versions_different_system_message(self):
        chunk = _make_chunk()
        a = build_extraction_messages(chunk, "v1", "v1")
        b = build_extraction_messages(chunk, "v2", "v1")
        assert a[0]["content"] != b[0]["content"]
