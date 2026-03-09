"""Run persistence."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Run


# Internal statuses considered "active" (only one per document allowed when policy forbids duplicate)
_ACTIVE_RUN_STATUSES = frozenset({"pending", "queued", "running"})


class RunRepository:
    """Persistence for processing runs. Session injected."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, run_id: str) -> Run | None:
        return self._session.get(Run, run_id)

    def get_active_run_for_document(self, document_id: str) -> Run | None:
        """Return an active run for this document if one exists (pending/queued/running)."""
        result = self._session.execute(
            select(Run).where(
                Run.document_id == document_id,
                Run.status.in_(_ACTIVE_RUN_STATUSES),
            ).limit(1)
        )
        return result.scalar_one_or_none()

    def save(self, run: Run) -> Run:
        self._session.add(run)
        self._session.flush()
        return run

    def update_status(self, run_id: str, status: str, **kwargs: object) -> None:
        run = self.get(run_id)
        if run is None:
            return
        run.status = status
        for key, value in kwargs.items():
            if hasattr(run, key):
                setattr(run, key, value)
        self._session.flush()
