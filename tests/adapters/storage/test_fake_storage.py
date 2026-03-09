"""Tests for in-memory fake storage. Use real checksum and keys; no mocks."""

import pytest

from app.core.checksum import sha256_hex
from app.core.errors import StorageNotFoundError
from app.adapters.storage.fake_storage import FakeObjectStorage


@pytest.fixture
def storage():
    return FakeObjectStorage()


# --- Upload: bytes and metadata ---


def test_put_bytes_stores_bytes_and_metadata(storage):
    body = b"hello world"
    storage.put_bytes("k1", body, "text/plain", {"original_filename": "x.txt"})
    meta = storage.head("k1")
    assert meta.size == len(body)
    assert meta.content_type == "text/plain"
    assert meta.metadata.get("original_filename") == "x.txt"
    assert meta.metadata.get("checksum_sha256") == sha256_hex(body)


def test_put_bytes_computes_checksum_when_not_provided(storage):
    body = b"data"
    storage.put_bytes("k", body, "application/octet-stream")
    meta = storage.head("k")
    assert meta.metadata["checksum_sha256"] == sha256_hex(body)


def test_put_bytes_records_size_correctly(storage):
    body = b"x" * 1000
    storage.put_bytes("k", body, "text/plain")
    assert storage.head("k").size == 1000


def test_put_file_uploads_from_path(storage, tmp_path):
    (tmp_path / "f.txt").write_bytes(b"file content")
    storage.put_file("key", tmp_path / "f.txt", "text/plain")
    meta = storage.head("key")
    assert meta.size == 12
    assert meta.metadata["checksum_sha256"] == sha256_hex(b"file content")
    assert storage.get_stream("key").read() == b"file content"


# --- Download ---


def test_get_stream_retrieves_expected_bytes(storage):
    body = b"retrieve me"
    storage.put_bytes("k", body, "text/plain")
    assert storage.get_stream("k").read() == body


def test_download_to_tempfile_writes_content_and_cleans_up(storage):
    body = b"temp content"
    storage.put_bytes("k", body, "text/plain")
    path = storage.download_to_tempfile("k")
    try:
        assert path.exists()
        assert path.read_bytes() == body
    finally:
        path.unlink(missing_ok=True)


def test_head_missing_key_raises_storage_not_found(storage):
    with pytest.raises(StorageNotFoundError, match="No object"):
        storage.head("nonexistent")


def test_get_stream_missing_key_raises_storage_not_found(storage):
    with pytest.raises(StorageNotFoundError, match="No object"):
        storage.get_stream("nonexistent").read()


def test_download_to_tempfile_missing_key_raises_storage_not_found(storage):
    with pytest.raises(StorageNotFoundError, match="No object"):
        storage.download_to_tempfile("nonexistent")


# --- Delete ---


def test_delete_removes_object(storage):
    storage.put_bytes("k", b"x", "text/plain")
    storage.delete("k")
    with pytest.raises(StorageNotFoundError):
        storage.head("k")


# --- Idempotency: repeated put overwrites ---


def test_repeated_put_bytes_overwrites(storage):
    storage.put_bytes("k", b"first", "text/plain")
    storage.put_bytes("k", b"second", "text/plain")
    meta = storage.head("k")
    assert meta.size == 6
    assert meta.metadata["checksum_sha256"] == sha256_hex(b"second")
    assert storage.get_stream("k").read() == b"second"
