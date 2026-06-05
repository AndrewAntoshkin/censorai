"""S3-compatible object storage (AWS S3, Cloudflare R2, MinIO)."""

from __future__ import annotations

import logging
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.client import Config

from app.core.config import settings

logger = logging.getLogger(__name__)


def object_storage_enabled() -> bool:
    return bool(settings.S3_BUCKET.strip() and settings.S3_ACCESS_KEY.strip())


def _bucket() -> str:
    return settings.S3_BUCKET.strip()


def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL.strip() or None,
        aws_access_key_id=settings.S3_ACCESS_KEY.strip(),
        aws_secret_access_key=settings.S3_SECRET_KEY.strip(),
        region_name=settings.S3_REGION.strip() or None,
        config=Config(signature_version="s3v4"),
    )


def build_object_key(project_id: str, filename: str) -> str:
    ext = Path(filename).suffix or ".mp4"
    return f"projects/{project_id}/{uuid.uuid4()}{ext}"


def upload_bytes(key: str, data: bytes, *, content_type: str = "video/mp4") -> str:
    client = _client()
    bucket = _bucket()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return f"s3://{bucket}/{key}"


def upload_file(key: str, source_path: Path, *, content_type: str = "video/mp4") -> str:
    client = _client()
    bucket = _bucket()
    client.upload_file(
        str(source_path),
        bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return f"s3://{bucket}/{key}"


def presign_put_upload(
    key: str,
    *,
    content_type: str = "video/mp4",
    size: int | None = None,
    ttl_seconds: int = 3600,
) -> dict:
    """Presigned PUT for direct browser upload to R2/S3."""
    bucket = _bucket()
    params: dict = {
        "Bucket": bucket,
        "Key": key,
        "ContentType": content_type,
    }
    if size is not None and size > 0:
        params["ContentLength"] = size
    upload_url = _client().generate_presigned_url(
        "put_object",
        Params=params,
        ExpiresIn=ttl_seconds,
    )
    storage_uri = f"s3://{bucket}/{key}"
    return {
        "upload_url": upload_url,
        "storage_path": storage_uri,
        "method": "PUT",
        "headers": {"Content-Type": content_type},
    }


def presigned_get_url(storage_uri: str, ttl_seconds: int | None = None) -> str:
    """Return HTTPS URL for s3://bucket/key or pass through http(s) URLs."""
    if storage_uri.startswith(("http://", "https://")):
        return storage_uri

    if not storage_uri.startswith("s3://"):
        raise ValueError(f"Not an object storage URI: {storage_uri}")

    parsed = urlparse(storage_uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip("/")
    ttl = ttl_seconds or settings.S3_PRESIGN_TTL_SECONDS
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=ttl,
    )


def _parse_s3_uri(storage_uri: str) -> tuple[str, str]:
    parsed = urlparse(storage_uri)
    return parsed.netloc, parsed.path.lstrip("/")


def download_object_to_tempfile(storage_uri: str) -> Path:
    """Download s3:// object to a temp file for local processing (e.g. ffmpeg)."""
    bucket, key = _parse_s3_uri(storage_uri)
    suffix = Path(key).suffix or ".mp4"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.close()
    dest = Path(tmp.name)
    _client().download_file(bucket, key, str(dest))
    logger.info("Downloaded %s for local processing (%s)", key, dest)
    return dest


def delete_objects_with_prefix(prefix: str) -> int:
    """Delete all keys under prefix in configured bucket. Returns count deleted."""
    if not object_storage_enabled():
        return 0
    bucket = _bucket()
    client = _client()
    deleted = 0
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        contents = page.get("Contents") or []
        if not contents:
            continue
        client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": obj["Key"]} for obj in contents]},
        )
        deleted += len(contents)
    if deleted:
        logger.info("Deleted %d S3 objects under %s", deleted, prefix)
    return deleted


def delete_object(storage_uri: str) -> None:
    if not storage_uri.startswith("s3://"):
        return
    bucket, key = _parse_s3_uri(storage_uri)
    _client().delete_object(Bucket=bucket, Key=key)
    logger.info("Deleted s3 object %s/%s", bucket, key)
