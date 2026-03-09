"""FastAPI dependencies: DB session, repos, services, storage, queue."""

from collections.abc import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from app.core.protocols import JobQueueProtocol, ObjectStorageProtocol
from app.db.repositories import (
    ActionRepository,
    ChunkRepository,
    DocumentRepository,
    RunEventRepository,
    RunRepository,
)
from app.services.ingest_service import IngestService


def get_db_session(
    request: Request,
) -> Generator[Session, None, None]:
    """Yield a DB session; commit on success (unless commit_db=False, e.g. tests), rollback on exception."""
    factory: sessionmaker[Session] = request.app.state.session_factory
    session = factory()
    commit = getattr(request.app.state, "commit_db", True)
    try:
        yield session
        if commit:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_storage(request: Request) -> ObjectStorageProtocol:
    """Return the object storage adapter from app state."""
    return request.app.state.storage


def get_queue(request: Request) -> JobQueueProtocol:
    """Return the job queue adapter from app state."""
    return request.app.state.queue


def get_document_repo(
    session: Session = Depends(get_db_session),
) -> DocumentRepository:
    return DocumentRepository(session)


def get_run_repo(
    session: Session = Depends(get_db_session),
) -> RunRepository:
    return RunRepository(session)


def get_chunk_repo(
    session: Session = Depends(get_db_session),
) -> ChunkRepository:
    return ChunkRepository(session)


def get_action_repo(
    session: Session = Depends(get_db_session),
) -> ActionRepository:
    return ActionRepository(session)


def get_run_event_repo(
    session: Session = Depends(get_db_session),
) -> RunEventRepository:
    return RunEventRepository(session)


def get_ingest_service(
    storage: ObjectStorageProtocol = Depends(get_storage),
    document_repo: DocumentRepository = Depends(get_document_repo),
) -> IngestService:
    return IngestService(storage, document_repo)


def get_metrics(request: Request):
    """Return the metrics recorder from app state (always set by create_app)."""
    return request.app.state.metrics
