"""In-memory fake object storage for tests. No network."""

import tempfile
from io import BytesIO
from pathlib import Path

from app.core.checksum import sha256_hex
from app.core.errors import StorageNotFoundError
from app.core.types import ObjectMetadata


class FakeObjectStorage:
    """In-memory implementation of object storage. Stores bytes, content_type, metadata."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[bytes, str, dict[str, str]]] = {}

    def put_bytes(
        self,
        key: str,
        body: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        meta = dict(metadata or {})
        if "checksum_sha256" not in meta:
            meta["checksum_sha256"] = sha256_hex(body)
        meta["size"] = str(len(body))
        self._store[key] = (body, content_type, meta)

    def put_file(
        self,
        key: str,
        file_path: str | Path,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        path = Path(file_path)
        body = path.read_bytes()
        self.put_bytes(key, body, content_type, metadata)

    def _get(self, key: str) -> tuple[bytes, str, dict[str, str]]:
        if key not in self._store:
            raise StorageNotFoundError(f"No object at key: {key!r}")
        return self._store[key]

    def get_stream(self, key: str) -> BytesIO:
        body, _, _ = self._get(key)
        return BytesIO(body)

    def download_to_tempfile(self, key: str) -> Path:
        body, _, _ = self._get(key)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
            f.write(body)
            return Path(f.name)

    def head(self, key: str) -> ObjectMetadata:
        body, content_type, meta = self._get(key)
        # Ensure size is in metadata for consistency
        meta = dict(meta)
        meta.setdefault("size", str(len(body)))
        return ObjectMetadata(size=len(body), content_type=content_type, metadata=meta)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
