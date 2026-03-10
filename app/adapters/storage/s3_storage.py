"""S3-compatible object storage adapter."""

import tempfile
from pathlib import Path
from io import BytesIO

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config.settings import S3Settings
from app.core.errors import PermanentExternalError, RetryableExternalError, StorageNotFoundError
from app.core.types import ObjectMetadata


def _full_key(key_prefix: str, key: str) -> str:
    if not key_prefix:
        return key
    prefix = key_prefix.rstrip("/")
    return f"{prefix}/{key}" if prefix else key


def _map_s3_error(e: Exception, key: str) -> None:
    """Map boto3/botocore errors to domain exceptions. Raises the mapped exception."""
    if isinstance(e, ClientError):
        code = e.response.get("Error", {}).get("Code", "")
        status = e.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
        if code == "404" or code == "NoSuchKey":
            raise StorageNotFoundError(f"Object not found: {key!r}") from e
        if status >= 500 or code in ("ServiceUnavailable", "InternalError", "SlowDown"):
            raise RetryableExternalError(f"S3 error (retryable): {code}") from e
        raise PermanentExternalError(f"S3 error: {code}") from e
    if isinstance(e, BotoCoreError):
        raise RetryableExternalError(f"S3 connection/timeout: {e!s}") from e
    raise PermanentExternalError(f"Storage error: {e!s}") from e


class S3ObjectStorage:
    """S3-compatible storage using boto3. Uses S3Settings for endpoint, bucket, key_prefix."""

    def __init__(self, settings: S3Settings) -> None:
        self._settings = settings
        kwargs = {
            "endpoint_url": settings.endpoint_url,
            "region_name": "us-east-1",
        }
        if (settings.access_key_id or "").strip():
            kwargs["aws_access_key_id"] = settings.access_key_id.strip()
            kwargs["aws_secret_access_key"] = (settings.secret_access_key or "").strip()
        self._client = boto3.client("s3", **kwargs)
        self._bucket = settings.bucket
        self._key_prefix = settings.key_prefix or ""

    def _key(self, key: str) -> str:
        return _full_key(self._key_prefix, key)

    def put_bytes(
        self,
        key: str,
        body: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        full_key = self._key(key)
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=full_key,
                Body=body,
                ContentType=content_type,
                Metadata=metadata or {},
            )
        except Exception as e:
            _map_s3_error(e, key)

    def put_file(
        self,
        key: str,
        file_path: str | Path,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        path = Path(file_path)
        full_key = self._key(key)
        try:
            self._client.upload_fileobj(
                path.open("rb"),
                self._bucket,
                full_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "Metadata": metadata or {},
                },
            )
        except Exception as e:
            _map_s3_error(e, key)

    def get_stream(self, key: str) -> BytesIO:
        full_key = self._key(key)
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=full_key)
            return BytesIO(resp["Body"].read())
        except Exception as e:
            _map_s3_error(e, key)

    def download_to_tempfile(self, key: str) -> Path:
        full_key = self._key(key)
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=full_key)
            body = resp["Body"].read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as f:
                f.write(body)
                return Path(f.name)
        except Exception as e:
            _map_s3_error(e, key)

    def head(self, key: str) -> ObjectMetadata:
        full_key = self._key(key)
        try:
            resp = self._client.head_object(Bucket=self._bucket, Key=full_key)
        except Exception as e:
            _map_s3_error(e, key)
        size = resp.get("ContentLength", 0)
        content_type = resp.get("ContentType", "application/octet-stream")
        meta = dict(resp.get("Metadata") or {})
        meta.setdefault("size", str(size))
        return ObjectMetadata(size=size, content_type=content_type, metadata=meta)

    def delete(self, key: str) -> None:
        full_key = self._key(key)
        try:
            self._client.delete_object(Bucket=self._bucket, Key=full_key)
        except Exception as e:
            _map_s3_error(e, key)
