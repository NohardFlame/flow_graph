"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def liveness():
    """Process is alive. Always 200."""
    return {"status": "ok"}


@router.get("/ready")
def readiness():
    """Ready to accept work. 200 when app is ready (e.g. DB optional for MVP)."""
    return {"status": "ready"}
