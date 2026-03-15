"""Fixtures for worker/orchestration tests. Real DB (rollback), fakes for parser/storage/LLM."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.storage.fake_storage import FakeObjectStorage
from app.config.settings import get_settings
from app.db.models import Document, DocumentVersion, Run
from app.db.session import get_engine
from app.db.repositories import (
    ActionRepository,
    ChunkRepository,
    DocumentRepository,
    RunEventRepository,
    RunRepository,
)
from app.services.chunk_assembler import ChunkAssembler
from app.services.run_orchestration.service import RunOrchestrator
from tests.fixtures.parse_fixtures import parsed_doc_simple_headings


@pytest.fixture(scope="module")
def test_dsn():
    return get_settings().postgres.dsn


@pytest.fixture(scope="module")
def engine(test_dsn):
    return get_engine(dsn=test_dsn)


@pytest.fixture
def db_connection(engine):
    connection = engine.connect()
    transaction = connection.begin()
    yield connection
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def session_factory(db_connection):
    return sessionmaker(
        bind=db_connection,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )


@pytest.fixture
def fake_storage():
    return FakeObjectStorage()


class FakeParser:
    """Returns a fixed ParsedDocument. Can be configured to raise on parse."""

    def __init__(self, document_id: str, run_id: str, parsed_doc=None, raise_on_parse: BaseException | None = None):
        self._document_id = document_id
        self._run_id = run_id
        self._parsed_doc = parsed_doc or parsed_doc_simple_headings(document_id=document_id, run_id=run_id)
        self._raise_on_parse = raise_on_parse

    def parse(self, source: bytes | str, content_type: str | None = None):
        if self._raise_on_parse:
            raise self._raise_on_parse
        return self._parsed_doc


class _IdGen:
    def generate(self) -> str:
        return str(uuid.uuid4())


class _Clock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


def _parser_factory(document_id: str, run_id: str):
    return FakeParser(document_id, run_id)


@pytest.fixture
def prefilter_service():
    from app.services.prefilter.service import PrefilterService
    base = Path(get_settings().prefilter.lexicon_dir)
    if not base.is_absolute():
        base = Path.cwd() / base
    return PrefilterService(lexicon_dir=str(base))


@pytest.fixture
def normalization_config():
    from app.core.normalization_config import load_normalization_config
    base = Path(get_settings().normalization.config_dir)
    if not base.is_absolute():
        base = Path.cwd() / base
    return load_normalization_config(base, require_dir=False)


@pytest.fixture
def orchestration_context(
    session_factory,
    fake_storage,
    prefilter_service,
    normalization_config,
):
    """Seed document/version/run in DB, put file in storage, build orchestrator. Same session for all."""
    from app.adapters.llm.fake_llm_adapter import FakeLLMAdapter

    session = session_factory()
    doc_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    storage_key = f"documents/{doc_id}/{version_id}/source.bin"
    fake_storage.put_bytes(storage_key, b"dummy content for parse", "text/plain")

    doc = Document(
        id=doc_id,
        original_filename="test.txt",
        content_type="text/plain",
        checksum_sha256="a" * 64,
        size_bytes=24,
        storage_key=storage_key,
        created_at=datetime.now(timezone.utc),
    )
    session.add(doc)
    session.flush()
    version = DocumentVersion(
        id=version_id,
        document_id=doc_id,
        version_number=1,
        source_storage_key=storage_key,
        source_parts_jsonb=None,
        created_at=datetime.now(timezone.utc),
    )
    session.add(version)
    session.flush()
    run = Run(
        id=run_id,
        document_id=doc_id,
        document_version_id=version_id,
        status="queued",
    )
    session.add(run)
    session.flush()

    orchestrator = RunOrchestrator(
        run_repo=RunRepository(session),
        document_repo=DocumentRepository(session),
        chunk_repo=ChunkRepository(session),
        action_repo=ActionRepository(session),
        run_event_repo=RunEventRepository(session),
        storage=fake_storage,
        parser_factory=_parser_factory,
        chunk_assembler=ChunkAssembler(),
        prefilter_service=prefilter_service,
        llm_adapter=FakeLLMAdapter(extraction_responses=['[{"verb": "submit", "primary_object": "form"}]'] * 50),
        normalization_config=normalization_config,
        id_generator=_IdGen(),
        clock=_Clock(),
        max_extract_retries=2,
        extraction_prompt_cfg={"prompt_version": "v1", "schema_version": "v1"},
    )
    yield orchestrator, run_id, session, fake_storage
