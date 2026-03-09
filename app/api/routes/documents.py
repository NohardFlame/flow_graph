"""Document upload and metadata endpoints."""

import logging
import uuid

from fastapi import APIRouter, Depends, File, UploadFile, Request, status

from app.api.schemas import DocumentCreatedResponse, DocumentResponse, RunCreatedResponse
from app.api.deps import get_document_repo, get_ingest_service, get_metrics, get_queue, get_run_repo
from app.config.logging import get_logger, log_structured
from app.config.settings import get_settings
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.db.repositories import DocumentRepository, RunRepository
from app.db.models import Run
from app.services.ingest_service import IngestService

router = APIRouter(prefix="/documents", tags=["documents"])
_log = get_logger(__name__)


def _allowed_extensions_set() -> set[str]:
    return {x.strip().lower() for x in get_settings().api.allowed_extensions.split(",") if x.strip()}


def _allowed_content_types_set() -> set[str]:
    return {x.strip().lower() for x in get_settings().api.allowed_content_types.split(",") if x.strip()}


def _validate_upload(filename: str, content_type: str, size: int) -> None:
    """Raise ValidationError if filename, size, or content type is invalid."""
    if not filename or not filename.strip():
        raise ValidationError("Filename is required")
    max_bytes = get_settings().api.max_upload_bytes
    if size > max_bytes:
        raise ValidationError(f"File size exceeds maximum allowed ({max_bytes} bytes)")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _allowed_extensions_set():
        raise ValidationError(f"File extension not allowed: {ext or '(none)'}")
    ct = (content_type or "").strip().lower().split(";")[0].strip()
    if ct and ct not in _allowed_content_types_set():
        raise ValidationError(f"Content type not allowed: {content_type or '(none)'}")


@router.post("", response_model=DocumentCreatedResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    ingest_service: IngestService = Depends(get_ingest_service),
    metrics=Depends(get_metrics),
):
    """Upload a document. Creates document and first version; does not create a run."""
    filename = file.filename or "unnamed"
    content_type = file.content_type or "application/octet-stream"
    # Read with limit to avoid loading unbounded data
    max_bytes = get_settings().api.max_upload_bytes
    body = await file.read(max_bytes + 1)
    if len(body) > max_bytes:
        raise ValidationError(f"File size exceeds maximum allowed ({max_bytes} bytes)")
    _validate_upload(filename, content_type, len(body))
    document = ingest_service.ingest(body, filename, content_type)
    metrics.record_document_uploaded()
    log_structured(
        _log,
        logging.INFO,
        "upload accepted; storage write complete",
        event="storage_write_complete",
        module="api.documents",
        document_id=document.id,
    )
    return DocumentCreatedResponse(
        id=document.id,
        original_filename=document.original_filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    document_repo: DocumentRepository = Depends(get_document_repo),
):
    """Return document metadata. 404 if not found."""
    document = document_repo.get(document_id)
    if document is None:
        raise NotFoundError(f"Document not found: {document_id}")
    return DocumentResponse(
        id=document.id,
        original_filename=document.original_filename,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        created_at=document.created_at,
    )


@router.post(
    "/{document_id}/runs",
    response_model=RunCreatedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_run(
    request: Request,
    document_id: str,
    document_repo: DocumentRepository = Depends(get_document_repo),
    run_repo: RunRepository = Depends(get_run_repo),
    queue=Depends(get_queue),
    metrics=Depends(get_metrics),
):
    """Create a run for the document and enqueue it. 404 if document missing; 409 if active run exists."""
    document = document_repo.get(document_id)
    if document is None:
        raise NotFoundError(f"Document not found: {document_id}")
    version = document_repo.get_latest_version(document_id)
    if version is None:
        raise NotFoundError(f"No version found for document: {document_id}")
    active = run_repo.get_active_run_for_document(document_id)
    if active is not None:
        raise ConflictError(
            f"Document already has an active run: {active.id}. Wait for it to finish or cancel."
        )
    run_id = str(uuid.uuid4())
    run = Run(
        id=run_id,
        document_id=document_id,
        document_version_id=version.id,
        status="queued",
    )
    run_repo.save(run)
    # Pass correlation_id so worker logs can be tied to this request
    payload = {"run_id": run_id}
    correlation_id = getattr(request.state, "correlation_id", "") or ""
    if correlation_id:
        payload["correlation_id"] = correlation_id
    queue.enqueue(payload)
    metrics.record_run_started()
    log_structured(
        _log,
        logging.INFO,
        "run created; job enqueued",
        event="run_created",
        module="api.documents",
        document_id=document_id,
        run_id=run_id,
        correlation_id=correlation_id or None,
    )
    return RunCreatedResponse(id=run_id, document_id=document_id)
