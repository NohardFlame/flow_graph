"""Fixtures for API tests. Uses test DB + fake storage + fake queue.

Run with: ENVIRONMENT=test POSTGRES_DB=app_test pytest tests/api -v
PostgreSQL must be running and migrations applied (alembic upgrade head).
If you see 'column "source_parts_jsonb" does not exist', run: alembic upgrade head
"""

import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.storage.fake_storage import FakeObjectStorage
from app.adapters.queue.fake_queue import FakeJobQueue
from app.api.app import create_app
from app.config.settings import get_settings
from app.db.session import get_engine


@pytest.fixture(scope="module")
def test_dsn():
    return get_settings().postgres.dsn


@pytest.fixture(scope="module")
def engine(test_dsn):
    return get_engine(dsn=test_dsn)


@pytest.fixture
def db_connection(engine):
    """One connection per test; transaction rolled back at end."""
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
def fake_object_storage():
    return FakeObjectStorage()


@pytest.fixture
def fake_queue():
    return FakeJobQueue()


@pytest.fixture
def api_client(session_factory, fake_object_storage, fake_queue):
    """TestClient with app wired to test DB (rollback), fake storage, fake queue."""
    app = create_app(storage=fake_object_storage, queue=fake_queue, session_factory=session_factory)
    app.state.commit_db = False
    return TestClient(app)


@pytest.fixture
def api_client_shared_session(db_connection, fake_object_storage, fake_queue):
    """TestClient that shares one session with the test (for seeding data without commit)."""
    from sqlalchemy.orm import Session
    session = Session(bind=db_connection, expire_on_commit=False)
    def factory():
        return session
    app = create_app(storage=fake_object_storage, queue=fake_queue, session_factory=factory)
    app.state.commit_db = False
    return TestClient(app), session


@pytest.fixture
def sample_multipart_file():
    """Minimal valid file for upload (text/plain, .txt)."""
    return ("sample.txt", io.BytesIO(b"hello world"), "text/plain")


@pytest.fixture
def correlation_id_headers():
    return {"X-Request-ID": "test-correlation-id-123"}
