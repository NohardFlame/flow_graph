"""Run status and run chunks/actions read endpoints."""

from fastapi import APIRouter, Depends, Query

from app.api.schemas import (
    ActionItem,
    ActionListResponse,
    ChunkItem,
    ChunkListResponse,
    RunEventItem,
    RunEventsResponse,
    RunResponse,
    internal_status_to_public,
)
from app.api.deps import (
    get_action_repo,
    get_chunk_repo,
    get_run_event_repo,
    get_run_repo,
)
from app.core.errors import NotFoundError
from app.db.repositories import ActionRepository, ChunkRepository, RunEventRepository, RunRepository

router = APIRouter(prefix="/runs", tags=["runs"])
@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: str,
    run_repo: RunRepository = Depends(get_run_repo),
):
    """Return run status and metadata. 404 if not found."""
    run = run_repo.get(run_id)
    if run is None:
        raise NotFoundError(f"Run not found: {run_id}")
    return RunResponse(
        id=run.id,
        document_id=run.document_id,
        status=internal_status_to_public(run.status),
        started_at=run.started_at,
        finished_at=run.finished_at,
        error_message=run.error_message,
        error_code=run.error_code,
        current_step=run.current_step,
    )


@router.get("/{run_id}/events", response_model=RunEventsResponse)
def get_run_events(
    run_id: str,
    run_repo: RunRepository = Depends(get_run_repo),
    run_event_repo: RunEventRepository = Depends(get_run_event_repo),
):
    """Return run step events for debugging. 404 if run not found."""
    run = run_repo.get(run_id)
    if run is None:
        raise NotFoundError(f"Run not found: {run_id}")
    events = run_event_repo.list_by_run(run_id)
    return RunEventsResponse(
        items=[
            RunEventItem(
                step=e.step,
                event_type=e.event_type,
                created_at=e.created_at,
                payload=e.payload_jsonb,
            )
            for e in events
        ]
    )


@router.get("/{run_id}/chunks", response_model=ChunkListResponse)
def get_run_chunks(
    run_id: str,
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0),
    run_repo: RunRepository = Depends(get_run_repo),
    chunk_repo: ChunkRepository = Depends(get_chunk_repo),
):
    """Return paginated chunks for the run. 404 if run not found."""
    run = run_repo.get(run_id)
    if run is None:
        raise NotFoundError(f"Run not found: {run_id}")
    total = chunk_repo.count_by_run(run_id)
    chunks = chunk_repo.list_by_run(run_id, limit=limit, offset=offset)
    return ChunkListResponse(
        items=[
            ChunkItem(
                id=c.id,
                chunk_hash=c.chunk_hash,
                text=c.text,
                estimated_tokens=c.estimated_tokens,
                prefilter_decision=c.prefilter_decision,
            )
            for c in chunks
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{run_id}/actions", response_model=ActionListResponse)
def get_run_actions(
    run_id: str,
    limit: int = Query(20, ge=1, le=500),
    offset: int = Query(0, ge=0),
    run_repo: RunRepository = Depends(get_run_repo),
    action_repo: ActionRepository = Depends(get_action_repo),
):
    """Return paginated actions for the run. 404 if run not found."""
    run = run_repo.get(run_id)
    if run is None:
        raise NotFoundError(f"Run not found: {run_id}")
    total = action_repo.count_by_run(run_id)
    actions = action_repo.list_by_run(run_id, limit=limit, offset=offset)
    return ActionListResponse(
        items=[
            ActionItem(
                id=a.id,
                action_label=a.action_label,
                action_canonical=a.action_canonical,
                confidence=a.confidence,
            )
            for a in actions
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
