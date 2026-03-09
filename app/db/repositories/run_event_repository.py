"""Run event persistence."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import RunEvent


class RunEventRepository:
    """Persistence for run step events."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        run_id: str,
        step: str,
        event_type: str,
        payload: dict | None = None,
    ) -> RunEvent:
        event = RunEvent(
            id=str(uuid.uuid4()),
            run_id=run_id,
            step=step,
            event_type=event_type,
            payload_jsonb=payload,
            created_at=datetime.now(timezone.utc),
        )
        self._session.add(event)
        self._session.flush()
        return event

    def list_by_run(self, run_id: str) -> list[RunEvent]:
        result = self._session.execute(
            select(RunEvent).where(RunEvent.run_id == run_id).order_by(RunEvent.created_at)
        )
        return list(result.scalars().all())
