"""Fixtures for DB tests. Use real PostgreSQL; set POSTGRES_* env (e.g. POSTGRES_DB=app_test).

To run Phase 1 DB tests:
  1. Start PostgreSQL.
  2. Create test DB: createdb app_test (or set POSTGRES_DB=app_test and create it).
  3. Apply migrations: ENVIRONMENT=test POSTGRES_DB=app_test alembic upgrade head
     (Required after adding new migrations, e.g. 002 source_parts_jsonb, 003 constituent_chunk_hashes.)
  4. Run: ENVIRONMENT=test POSTGRES_DB=app_test pytest tests/db -v
"""

import pytest
from sqlalchemy.orm import Session as SessionType

from app.config.settings import get_settings
from app.db.repositories import (
    ActionRepository,
    ChunkRepository,
    DocumentRepository,
    LLMCallRepository,
    RunEventRepository,
    RunRepository,
)
from app.db.session import get_engine


@pytest.fixture(scope="module")
def test_dsn():
    """DSN for test DB. Uses POSTGRES_* from env (e.g. POSTGRES_DB=app_test)."""
    return get_settings().postgres.dsn


@pytest.fixture(scope="module")
def engine(test_dsn):
    """Engine for test DB."""
    return get_engine(dsn=test_dsn)


@pytest.fixture(scope="module")
def session_factory(engine):
    """Session factory bound to test DB."""
    from sqlalchemy.orm import sessionmaker
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=SessionType,
    )


@pytest.fixture
def db_session(engine):
    """Session that rolls back after each test. Isolates tests."""
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionType(bind=connection, expire_on_commit=False)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def document_repo(db_session):
    return DocumentRepository(db_session)


@pytest.fixture
def run_repo(db_session):
    return RunRepository(db_session)


@pytest.fixture
def chunk_repo(db_session):
    return ChunkRepository(db_session)


@pytest.fixture
def llm_call_repo(db_session):
    return LLMCallRepository(db_session)


@pytest.fixture
def action_repo(db_session):
    return ActionRepository(db_session)


@pytest.fixture
def run_event_repo(db_session):
    return RunEventRepository(db_session)


# Factory helpers: build model instances for tests (caller sets id and required fields)

def document_factory(
    document_id: str,
    *,
    original_filename: str = "test.pdf",
    content_type: str = "application/pdf",
    checksum_sha256: str = "a" * 64,
    size_bytes: int = 100,
    storage_key: str = "documents/test/key",
    created_at=None,
):
    from datetime import datetime, timezone
    from app.db.models import Document
    return Document(
        id=document_id,
        original_filename=original_filename,
        content_type=content_type,
        checksum_sha256=checksum_sha256,
        size_bytes=size_bytes,
        storage_key=storage_key,
        created_at=created_at or datetime.now(timezone.utc),
    )


def document_version_factory(
    version_id: str,
    document_id: str,
    *,
    source_storage_key: str,
    version_number: int = 1,
    source_parts_jsonb: list[dict[str, str]] | None = None,
):
    from datetime import datetime, timezone
    from app.db.models import DocumentVersion
    return DocumentVersion(
        id=version_id,
        document_id=document_id,
        version_number=version_number,
        source_storage_key=source_storage_key,
        source_parts_jsonb=source_parts_jsonb,
        created_at=datetime.now(timezone.utc),
    )


def run_factory(
    run_id: str,
    document_id: str,
    document_version_id: str,
    *,
    status: str = "pending",
):
    from app.db.models import Run
    return Run(
        id=run_id,
        document_id=document_id,
        document_version_id=document_version_id,
        status=status,
    )


def chunk_factory(run_id: str, chunk_hash: str, text: str, *, prefilter_decision: str | None = None):
    import uuid
    from app.db.models import Chunk
    return Chunk(
        id=str(uuid.uuid4()),
        run_id=run_id,
        chunk_hash=chunk_hash,
        text=text,
        prefilter_decision=prefilter_decision,
    )


def action_factory(
    action_id: str,
    run_id: str,
    action_label: str,
    action_canonical: str,
    *,
    chunk_id: str | None = None,
    raw_jsonb: dict | None = None,
):
    from app.db.models import Action
    return Action(
        id=action_id,
        run_id=run_id,
        chunk_id=chunk_id,
        action_label=action_label,
        action_canonical=action_canonical,
        raw_jsonb=raw_jsonb,
    )


def action_evidence_factory(evidence_id: str, action_id: str, snippet: str):
    from app.db.models import ActionEvidence
    return ActionEvidence(id=evidence_id, action_id=action_id, snippet=snippet)


def llm_call_factory(llm_call_id: str, run_id: str, *, chunk_id: str | None = None):
    from app.db.models import LLMCall
    return LLMCall(id=llm_call_id, run_id=run_id, chunk_id=chunk_id)
