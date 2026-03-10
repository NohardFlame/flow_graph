"""ASGI entry point. Create app with storage and queue wired from environment.

Set USE_FAKE_ADAPTERS=1 for local dev without S3/Redis. Otherwise S3 and ARQ are used.
Tests inject fakes explicitly via create_app().
"""

from app.api.wiring import get_storage, get_queue
from app.api.app import create_app
from app.db.session import get_session_factory

_storage = get_storage()
_queue = get_queue()
_session_factory = get_session_factory()

app = create_app(storage=_storage, queue=_queue, session_factory=_session_factory)
