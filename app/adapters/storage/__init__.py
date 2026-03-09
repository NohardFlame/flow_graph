"""Object storage adapters."""

from app.adapters.storage.fake_storage import FakeObjectStorage
from app.adapters.storage.s3_storage import S3ObjectStorage

__all__ = ["FakeObjectStorage", "S3ObjectStorage"]
