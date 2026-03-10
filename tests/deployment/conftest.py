"""Fixtures for deployment tests. Isolate env for subprocess tests; provide session_factory for readiness."""

import os
import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings
from app.db.session import get_engine


@pytest.fixture
def subprocess_env_no_environment():
    """Minimal env for subprocess that deliberately omits ENVIRONMENT so config fails."""
    env = os.environ.copy()
    env.pop("ENVIRONMENT", None)
    return env


@pytest.fixture
def subprocess_env_minimal_valid():
    """Minimal env for subprocess that has required vars (for tests that need valid config)."""
    env = os.environ.copy()
    env.setdefault("ENVIRONMENT", "test")
    env.setdefault("POSTGRES_DB", "app_test")
    env.setdefault("POSTGRES_USER", "postgres")
    env.setdefault("POSTGRES_PASSWORD", "postgres")
    env.setdefault("POSTGRES_HOST", "localhost")
    env.setdefault("POSTGRES_PORT", "5432")
    return env


@pytest.fixture(scope="module")
def _deployment_engine():
    """Engine for deployment tests (test DB). Requires ENVIRONMENT=test, POSTGRES_* set."""
    return get_engine(dsn=get_settings().postgres.dsn)


@pytest.fixture
def session_factory(_deployment_engine):
    """Session factory bound to test DB for readiness tests (one connection per test)."""
    connection = _deployment_engine.connect()
    transaction = connection.begin()
    try:
        yield sessionmaker(
            bind=connection,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            class_=Session,
        )
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()
