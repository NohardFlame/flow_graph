"""Build storage and queue from settings. Used by API main entrypoint.

When USE_FAKE_ADAPTERS=1 (or true), use in-memory fakes so the API runs without
S3 or Redis. Otherwise use S3ObjectStorage and ARQJobQueue from get_settings().
"""

from app.config.settings import get_settings
from app.adapters.storage.fake_storage import FakeObjectStorage
from app.adapters.storage.s3_storage import S3ObjectStorage
from app.adapters.queue.fake_queue import FakeJobQueue
from app.adapters.queue.arq_queue import ARQJobQueue


def get_storage():
    """Return storage adapter: FakeObjectStorage if USE_FAKE_ADAPTERS else S3ObjectStorage."""
    settings = get_settings()
    if settings.use_fake_adapters:
        return FakeObjectStorage()
    return S3ObjectStorage(settings.s3)


def get_queue():
    """Return queue adapter: FakeJobQueue if USE_FAKE_ADAPTERS else ARQJobQueue."""
    settings = get_settings()
    if settings.use_fake_adapters:
        return FakeJobQueue()
    return ARQJobQueue()
