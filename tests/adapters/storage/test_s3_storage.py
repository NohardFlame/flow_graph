"""S3 adapter tests: exception mapping only. Mock boto3 at client boundary."""

from unittest.mock import patch

import pytest
from botocore.exceptions import BotoCoreError, ClientError

from app.adapters.storage.s3_storage import S3ObjectStorage
from app.config.settings import S3Settings
from app.core.errors import PermanentExternalError, RetryableExternalError, StorageNotFoundError


@pytest.fixture
def s3_settings():
    return S3Settings(endpoint_url="http://localhost:9000", bucket="test", key_prefix="")


def test_head_404_maps_to_storage_not_found(s3_settings):
    """Vendor 404 must become StorageNotFoundError, not raw ClientError."""
    storage = S3ObjectStorage(s3_settings)
    error_response = {"Error": {"Code": "404", "Message": "Not Found"}, "ResponseMetadata": {"HTTPStatusCode": 404}}
    with pytest.raises(StorageNotFoundError, match="not found"):
        with patch.object(storage._client, "head_object", side_effect=ClientError(error_response, "HeadObject")):
            storage.head("some/key")


def test_head_no_such_key_maps_to_storage_not_found(s3_settings):
    error_response = {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}, "ResponseMetadata": {"HTTPStatusCode": 404}}
    storage = S3ObjectStorage(s3_settings)
    with pytest.raises(StorageNotFoundError, match="not found"):
        with patch.object(storage._client, "head_object", side_effect=ClientError(error_response, "HeadObject")):
            storage.head("missing")


def test_head_503_maps_to_retryable(s3_settings):
    error_response = {"Error": {"Code": "ServiceUnavailable", "Message": "Slow down"}, "ResponseMetadata": {"HTTPStatusCode": 503}}
    storage = S3ObjectStorage(s3_settings)
    with pytest.raises(RetryableExternalError, match="retryable"):
        with patch.object(storage._client, "head_object", side_effect=ClientError(error_response, "HeadObject")):
            storage.head("key")


def test_head_403_maps_to_permanent(s3_settings):
    error_response = {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}, "ResponseMetadata": {"HTTPStatusCode": 403}}
    storage = S3ObjectStorage(s3_settings)
    with pytest.raises(PermanentExternalError, match="S3 error"):
        with patch.object(storage._client, "head_object", side_effect=ClientError(error_response, "HeadObject")):
            storage.head("key")


def test_put_bytes_connection_error_maps_to_retryable(s3_settings):
    storage = S3ObjectStorage(s3_settings)
    with pytest.raises(RetryableExternalError, match="connection|timeout"):
        with patch.object(storage._client, "put_object", side_effect=BotoCoreError()):
            storage.put_bytes("k", b"data", "text/plain")
