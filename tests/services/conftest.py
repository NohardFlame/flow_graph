"""Fixtures for service tests. Ingest tests use real DB (same as tests/db).

To run ingest tests: start PostgreSQL, create app_test, run migrations, then:
  ENVIRONMENT=test POSTGRES_DB=app_test [POSTGRES_PASSWORD=...] pytest tests/services -v
"""

import pytest
from sqlalchemy.orm import Session as SessionType

from app.config.settings import get_settings
from app.db.repositories import DocumentRepository
from app.db.session import get_engine


@pytest.fixture(scope="module")
def test_dsn():
    return get_settings().postgres.dsn


@pytest.fixture(scope="module")
def engine(test_dsn):
    return get_engine(dsn=test_dsn)


@pytest.fixture
def db_session(engine):
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
def fake_storage():
    from app.adapters.storage.fake_storage import FakeObjectStorage
    return FakeObjectStorage()
