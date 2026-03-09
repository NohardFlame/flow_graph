"""Tests for deterministic storage key builders. No mocks."""

import pytest

from app.core.storage_keys import (
    debug_prefix,
    llm_artifact_key,
    parsed_artifact_key,
    raw_source_key,
)


# --- raw_source_key: deterministic, extension from content_type ---


def test_raw_source_key_deterministic():
    a = raw_source_key("doc-1", "ver-1", "application/pdf")
    b = raw_source_key("doc-1", "ver-1", "application/pdf")
    assert a == b
    assert a == "raw/doc-1/ver-1/source.pdf"


def test_raw_source_key_extension_from_content_type():
    assert raw_source_key("d", "v", "application/pdf").endswith(".pdf")
    assert raw_source_key("d", "v", "application/json").endswith(".json")
    assert raw_source_key("d", "v", "text/plain").endswith(".txt")
    assert raw_source_key("d", "v", "application/octet-stream").endswith(".bin")


def test_raw_source_key_user_filename_not_in_key():
    """Key must not depend on filename; extension from content_type only."""
    key1 = raw_source_key("doc", "ver", "application/pdf")
    key2 = raw_source_key("doc", "ver", "application/pdf")
    assert key1 == key2
    assert "malicious" not in key1
    assert ".." not in key1


def test_raw_source_key_rejects_unsafe_document_id():
    with pytest.raises(ValueError, match="document_id"):
        raw_source_key("../etc", "ver", "application/pdf")
    with pytest.raises(ValueError, match="invalid path"):
        raw_source_key("doc/extra", "ver", "application/pdf")


def test_raw_source_key_rejects_unsafe_version_id():
    with pytest.raises(ValueError, match="version_id"):
        raw_source_key("doc", "..", "application/pdf")


# --- parsed_artifact_key: includes run_id and document_id ---


def test_parsed_artifact_key_includes_run_id_and_document_id():
    key = parsed_artifact_key("doc-1", "run-2", "docling")
    assert "doc-1" in key
    assert "run-2" in key
    assert key == "parsed/doc-1/run-2/docling.json"


def test_parsed_artifact_key_markdown():
    assert parsed_artifact_key("d", "r", "markdown") == "parsed/d/r/document.md"


def test_parsed_artifact_key_chunk_manifest():
    assert parsed_artifact_key("d", "r", "chunk_manifest") == "parsed/d/r/chunk_manifest.json"


def test_parsed_artifact_key_invalid_artifact():
    with pytest.raises(ValueError, match="Unknown artifact"):
        parsed_artifact_key("d", "r", "invalid")  # type: ignore[arg-type]


# --- llm_artifact_key ---


def test_llm_artifact_key_request():
    key = llm_artifact_key("doc", "run", "chunk", "request")
    assert key == "llm/doc/run/chunk/request.json"


def test_llm_artifact_key_response():
    key = llm_artifact_key("doc", "run", "chunk", "response")
    assert key == "llm/doc/run/chunk/response.json"


# --- debug_prefix ---


def test_debug_prefix_trailing_slash():
    p = debug_prefix("doc", "run")
    assert p == "debug/doc/run/"
    assert p.endswith("/")


# --- path escape: user-supplied filename cannot escape ---


def test_path_segments_only_safe_chars():
    """IDs with only [a-zA-Z0-9_-] are accepted; no .. or slashes."""
    raw_source_key("a1-b_2", "v1", "application/pdf")
    with pytest.raises(ValueError):
        raw_source_key("a b", "v", "application/pdf")  # space not allowed
