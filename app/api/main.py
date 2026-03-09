"""ASGI entry point. Create app with storage and queue wired.

For local development without S3/Redis, fakes are used (set USE_FAKE_ADAPTERS=1 or run tests).
For production, wire real storage and queue here or via env.
"""

from app.adapters.queue.fake_queue import FakeJobQueue
from app.adapters.storage.fake_storage import FakeObjectStorage
from app.api.app import create_app
from app.db.session import get_session_factory

# Local dev: use fakes so API runs without S3 or queue backend
_storage = FakeObjectStorage()
_queue = FakeJobQueue()
_session_factory = get_session_factory()

app = create_app(storage=_storage, queue=_queue, session_factory=_session_factory)
