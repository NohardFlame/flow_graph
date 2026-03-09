"""Persist parse and chunk debug artifacts to object storage for inspection without rerunning Docling."""

import json

from app.core.protocols import ObjectStorageProtocol
from app.core.storage_keys import parsed_artifact_key
from app.core.types import DocumentId, RunId
from app.domain.parse_models import ExtractionChunk, ParsedDocument
from app.core.types import DocumentId, RunId
from app.domain.parse_models import ExtractionChunk, ParsedDocument


def save_parse_artifacts(
    storage: ObjectStorageProtocol,
    document_id: DocumentId,
    run_id: RunId,
    parsed_document: ParsedDocument,
    chunks: list[ExtractionChunk],
    *,
    markdown_body: str | None = None,
) -> None:
    """Write structured parse export and chunk manifest to storage. Uses parsed_artifact_key."""
    # Structured parse export (simplified for debug: sections, title, format)
    parse_export = {
        "document_id": parsed_document.document_id,
        "run_id": parsed_document.run_id,
        "source_format": parsed_document.source_format,
        "title": parsed_document.title,
        "sections": [
            {
                "section_path": u.section_path,
                "block_type": str(u.block_type),
                "text_preview": u.text[:500] + "..." if len(u.text) > 500 else u.text,
            }
            for u in parsed_document.sections
        ],
        "tables_count": len(parsed_document.tables),
        "lists_count": len(parsed_document.lists),
    }
    if parsed_document.raw_docling_export_ref:
        parse_export["raw_docling_ref_keys"] = list(parsed_document.raw_docling_export_ref.keys())[:20]

    key_docling = parsed_artifact_key(document_id, run_id, "docling")
    storage.put_bytes(key_docling, json.dumps(parse_export, indent=2).encode("utf-8"), "application/json")

    # Chunk manifest: chunk ids and source spans
    chunk_manifest = [
        {
            "chunk_id": c.chunk_id,
            "section_path": c.section_path,
            "estimated_tokens": c.estimated_tokens,
            "source_spans": c.source_spans,
        }
        for c in chunks
    ]
    key_manifest = parsed_artifact_key(document_id, run_id, "chunk_manifest")
    storage.put_bytes(key_manifest, json.dumps(chunk_manifest, indent=2).encode("utf-8"), "application/json")

    if markdown_body is not None:
        key_md = parsed_artifact_key(document_id, run_id, "markdown")
        storage.put_bytes(key_md, markdown_body.encode("utf-8"), "text/markdown")
