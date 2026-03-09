"""Action and action_evidence persistence.

Idempotency: upsert by (run_id, action_canonical). If a row with the same
run_id and action_canonical exists, we update it; otherwise insert.
Evidence rows are replaced for that action (delete existing, insert new).
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Action, ActionEvidence


class ActionRepository:
    """Persistence for extracted actions and evidence."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, action_id: str) -> Action | None:
        return self._session.get(Action, action_id)

    def save(self, action: Action, *, evidence: list[ActionEvidence] | None = None) -> Action:
        existing = self._session.execute(
            select(Action).where(
                Action.run_id == action.run_id,
                Action.action_canonical == action.action_canonical,
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.action_label = action.action_label
            existing.chunk_id = action.chunk_id
            existing.primary_actor_key = action.primary_actor_key
            existing.primary_object_key = action.primary_object_key
            existing.input_state_key = action.input_state_key
            existing.output_state_key = action.output_state_key
            existing.confidence = action.confidence
            existing.raw_jsonb = action.raw_jsonb
            existing.normalization_version = action.normalization_version
            if evidence is not None:
                for e in existing.evidence:
                    self._session.delete(e)
                for e in evidence:
                    e.action_id = existing.id
                    self._session.add(e)
            self._session.flush()
            return existing
        self._session.add(action)
        if evidence:
            for e in evidence:
                e.action_id = action.id
                self._session.add(e)
        self._session.flush()
        return action

    def list_by_run(self, run_id: str, limit: int | None = None, offset: int = 0) -> list[Action]:
        q = select(Action).where(Action.run_id == run_id).order_by(Action.id).offset(offset)
        if limit is not None:
            q = q.limit(limit)
        result = self._session.execute(q)
        return list(result.scalars().all())

    def count_by_run(self, run_id: str) -> int:
        """Return total number of actions for the run (for pagination)."""
        result = self._session.execute(
            select(func.count()).select_from(Action).where(Action.run_id == run_id)
        )
        return result.scalar_one() or 0
