"""Deterministic object storage key builders.

Keys are derived from content_type and IDs only; never use user-supplied
filename in the key path. Extension is from content_type with a safe fallback.
"""

import re
from typing import Literal

# Safe extension from content_type (subset of mimetypes.guess_extension)
_CONTENT_TYPE_TO_EXT: dict[str, str] = {
    "application/pdf": "pdf",
    "application/json": "json",
    "text/plain": "txt",
    "text/markdown": "md",
    "text/html": "html",
    "application/xml": "xml",
    "text/csv": "csv",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}
_DEFAULT_EXT = "bin"

# Only allow segments that cannot escape (no .., no control chars, no empty)
_SAFE_SEGMENT_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _extension_from_content_type(content_type: str) -> str:
    """Return safe file extension for content_type. Never use user input."""
    if not content_type or not isinstance(content_type, str):
        return _DEFAULT_EXT
    # Normalize: take first part if e.g. "application/pdf; charset=utf-8"
    normalized = content_type.split(";")[0].strip().lower()
    return _CONTENT_TYPE_TO_EXT.get(normalized, _DEFAULT_EXT)


def _safe_segment(segment: str, name: str) -> str:
    """Return segment if safe; otherwise raise. Prevents path escape."""
    if not segment or not isinstance(segment, str):
        raise ValueError(f"{name} must be a non-empty string")
    if "\0" in segment or ".." in segment or "/" in segment or "\\" in segment:
        raise ValueError(f"{name} contains invalid path characters")
    if not _SAFE_SEGMENT_RE.match(segment):
        raise ValueError(f"{name} may only contain [a-zA-Z0-9_-]")
    return segment


def raw_source_key(document_id: str, version_id: str, content_type: str) -> str:
    """Key for raw uploaded source file. Deterministic.

    Pattern: raw/{document_id}/{version_id}/source.{ext}
    Extension is derived from content_type only (filename is metadata only).
    """
    doc = _safe_segment(document_id, "document_id")
    ver = _safe_segment(version_id, "version_id")
    ext = _extension_from_content_type(content_type)
    return f"raw/{doc}/{ver}/source.{ext}"


def raw_source_part_key(
    document_id: str, version_id: str, part_index: int, content_type: str
) -> str:
    """Key for one part of a multi-file document version. Deterministic.

    Pattern: raw/{document_id}/{version_id}/part_{part_index}.{ext}
    """
    doc = _safe_segment(document_id, "document_id")
    ver = _safe_segment(version_id, "version_id")
    ext = _extension_from_content_type(content_type)
    return f"raw/{doc}/{ver}/part_{part_index}.{ext}"


def parsed_artifact_key(
    document_id: str,
    run_id: str,
    artifact: Literal["docling", "markdown", "chunk_manifest"],
) -> str:
    """Key for parsed run artifacts. Includes run_id."""
    doc = _safe_segment(document_id, "document_id")
    run = _safe_segment(run_id, "run_id")
    if artifact == "docling":
        return f"parsed/{doc}/{run}/docling.json"
    if artifact == "markdown":
        return f"parsed/{doc}/{run}/document.md"
    if artifact == "chunk_manifest":
        return f"parsed/{doc}/{run}/chunk_manifest.json"
    raise ValueError(f"Unknown artifact: {artifact!r}")


def llm_artifact_key(
    document_id: str,
    run_id: str,
    chunk_id: str,
    kind: Literal["request", "response"],
) -> str:
    """Key for LLM request/response artifact."""
    doc = _safe_segment(document_id, "document_id")
    run = _safe_segment(run_id, "run_id")
    chunk = _safe_segment(chunk_id, "chunk_id")
    if kind == "request":
        return f"llm/{doc}/{run}/{chunk}/request.json"
    if kind == "response":
        return f"llm/{doc}/{run}/{chunk}/response.json"
    raise ValueError(f"Unknown kind: {kind!r}")


def debug_prefix(document_id: str, run_id: str) -> str:
    """Prefix for debug artifacts under a run. Trailing slash for listing."""
    doc = _safe_segment(document_id, "document_id")
    run = _safe_segment(run_id, "run_id")
    return f"debug/{doc}/{run}/"
