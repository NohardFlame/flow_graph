"""Worker task entrypoint: process run job from queue payload."""

from typing import Any, Callable

from sqlalchemy.orm import Session

from app.workers.retry_policy import is_run_step_retryable
from app.workers.schemas import RunJobPayload


def process_run_job(
    payload: dict[str, Any],
    *,
    session_factory: Callable[[], Session] | None = None,
    orchestrator_factory: Callable[[Session], Any] | None = None,
) -> None:
    """Deserialize payload, run pipeline, commit or mark failed. Re-raise if retryable.

    Caller provides session_factory and/or orchestrator_factory (e.g. from app state or tests).
    If orchestrator_factory is None, uses app.workers.deps.build_orchestrator with session_factory
    from app.db.session.get_session_factory() when session_factory is also None.
    """
    job = RunJobPayload.from_dict(payload)
    if session_factory is None:
        from app.db.session import get_session_factory
        session_factory = get_session_factory()
    if orchestrator_factory is None:
        from app.workers.deps import build_orchestrator
        orchestrator_factory = build_orchestrator

    session = session_factory()
    try:
        orchestrator = orchestrator_factory(session)
        orchestrator.execute_run(job.run_id, correlation_id=job.correlation_id)
        session.commit()
    except Exception as e:
        session.rollback()
        if is_run_step_retryable(e):
            raise
        # Permanent failure: run already marked failed in execute_run
        raise
    finally:
        session.close()
