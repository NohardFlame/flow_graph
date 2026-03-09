"""Health check endpoints."""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def liveness():
    """Process is alive. Always 200."""
    return {"status": "ok"}


@router.get("/ready")
def readiness(request: Request):
    """Ready to accept work. 200 when DB (and Redis if queue has ping) are reachable; 503 otherwise."""
    checks: dict[str, str] = {}
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is not None:
        try:
            session = session_factory()
            try:
                session.execute(text("SELECT 1"))
                checks["db"] = "ok"
            finally:
                session.close()
        except Exception:
            checks["db"] = "unavailable"
    else:
        checks["db"] = "ok"  # no factory wired
    queue = getattr(request.app.state, "queue", None)
    if queue is not None and hasattr(queue, "ping"):
        try:
            if queue.ping():
                checks["redis"] = "ok"
            else:
                checks["redis"] = "unavailable"
        except Exception:
            checks["redis"] = "unavailable"
    else:
        checks["redis"] = "ok"  # no queue or no ping method
    if any(v == "unavailable" for v in checks.values()):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "checks": checks},
        )
    return {"status": "ready", "checks": checks}
