"""SQLAlchemy engine and session factory. One transaction per operation."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import get_settings


def get_engine(dsn: str | None = None):
    """Create engine from DSN. Uses settings.postgres.dsn if dsn is None."""
    url = dsn if dsn is not None else get_settings().postgres.dsn
    return create_engine(
        url,
        pool_pre_ping=True,
        echo=False,
    )


def get_session_factory(dsn: str | None = None):
    """Return a session factory bound to an engine. Pass dsn in tests for test DB."""
    engine = get_engine(dsn=dsn)
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=Session,
    )


@contextmanager
def get_session(dsn: str | None = None) -> Generator[Session, None, None]:
    """Context manager: one transaction per use. Commits on exit, rolls back on exception.
    Do not share one session across concurrent tasks.
    """
    factory = get_session_factory(dsn=dsn)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
