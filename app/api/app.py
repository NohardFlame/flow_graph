"""FastAPI app factory: routes, exception handlers, correlation ID middleware."""

import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import documents, health, runs
from app.api.schemas import ErrorResponse
from app.core.errors import (
    ConflictError,
    DomainError,
    NotFoundError,
    StorageError,
    ValidationError,
)

CORRELATION_ID_HEADER = "X-Request-ID"
CORRELATION_ID_STATE_KEY = "correlation_id"


def get_correlation_id(request: Request) -> str:
    """Return correlation id from request state (set by middleware)."""
    return getattr(request.state, CORRELATION_ID_STATE_KEY, "") or ""


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Set correlation id from X-Request-ID or generate; add to response headers."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response


def _error_response(
    detail: str,
    code: str,
    status_code: int,
    correlation_id: str | None = None,
) -> JSONResponse:
    body = ErrorResponse(detail=detail, code=code, correlation_id=correlation_id)
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(exclude_none=True),
    )


async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    return _error_response(
        detail=exc.message,
        code="not_found",
        status_code=status.HTTP_404_NOT_FOUND,
        correlation_id=getattr(request.state, CORRELATION_ID_STATE_KEY, None),
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return _error_response(
        detail=exc.message,
        code="validation_error",
        status_code=status.HTTP_400_BAD_REQUEST,
        correlation_id=getattr(request.state, CORRELATION_ID_STATE_KEY, None),
    )


async def conflict_error_handler(request: Request, exc: ConflictError) -> JSONResponse:
    return _error_response(
        detail=exc.message,
        code="conflict",
        status_code=status.HTTP_409_CONFLICT,
        correlation_id=getattr(request.state, CORRELATION_ID_STATE_KEY, None),
    )


async def storage_error_handler(request: Request, exc: StorageError) -> JSONResponse:
    return _error_response(
        detail=exc.message,
        code="storage_error",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        correlation_id=getattr(request.state, CORRELATION_ID_STATE_KEY, None),
    )


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return _error_response(
        detail=exc.message,
        code="error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        correlation_id=getattr(request.state, CORRELATION_ID_STATE_KEY, None),
    )


def create_app(
    storage: Any,
    queue: Any,
    session_factory: Any = None,
    metrics: Any = None,
) -> FastAPI:
    """Create FastAPI app with routes and dependencies. Caller wires storage and queue."""
    from app.db.session import get_session_factory
    from app.core.metrics import NoOpMetricsRecorder

    app = FastAPI(title="flow-graph", version="0.1.0")
    app.add_middleware(CorrelationIdMiddleware)

    app.state.storage = storage
    app.state.queue = queue
    app.state.session_factory = session_factory or get_session_factory()
    app.state.metrics = metrics if metrics is not None else NoOpMetricsRecorder()

    app.include_router(documents.router)
    app.include_router(runs.router)
    app.include_router(health.router)

    static_dir = Path(__file__).resolve().parent.parent / "static"
    if static_dir.is_dir():
        app.mount("/ui", StaticFiles(directory=str(static_dir), html=True), name="ui")

    app.add_exception_handler(NotFoundError, not_found_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(ConflictError, conflict_error_handler)
    app.add_exception_handler(StorageError, storage_error_handler)
    app.add_exception_handler(DomainError, domain_error_handler)

    return app
