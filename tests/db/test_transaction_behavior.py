"""Transaction behavior: rollback on failure."""

import uuid

from app.db.repositories import DocumentRepository
from app.db.session import get_session_factory
from tests.db.conftest import document_factory, test_dsn


class TestTransactionRollback:
    def test_rollback_prevents_commit(self, test_dsn):
        """When we roll back, data is not visible in a new session."""
        factory = get_session_factory(dsn=test_dsn)
        session = factory()
        repo = DocumentRepository(session)
        doc_id = str(uuid.uuid4())
        doc = document_factory(doc_id)
        repo.save(doc)
        session.rollback()
        session.close()

        session2 = factory()
        repo2 = DocumentRepository(session2)
        loaded = repo2.get(doc_id)
        session2.close()
        assert loaded is None
