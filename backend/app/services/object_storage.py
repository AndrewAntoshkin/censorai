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
    return bool(
        settings.S3_BUCKET.strip()
        and settings.S3_ACCESS_KEY.strip()
        and settings.S3_SECRET_KEY.strip()
        and settings.S3_ENDPOINT_URL.strip()
    )


def _endpoint_url() -> str | None:
    url = settings.S3_ENDPOINT_URL.strip().rstrip("/")
    return url or None


def _client():
    return boto3.client(
        "s3",
        endpoint_url=_endpoint_url(),
        aws_access_key_id=settings.S3_ACCESS_KEY.strip(),
        aws_secret_access_key=settings.S3_SECRET_KEY.strip(),
        region_name=settings.S3_REGION.strip() or "auto",
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


def _bucket() -> str:
    return settings.S3_BUCKET.strip()


def verify_presign_works() -> None:
    """Raise if R2/S3 credentials or presign config are invalid."""
    presign_put_upload(
        f"selftest/presign-probe-{uuid.uuid4().hex[:8]}.txt",
        content_type="text/plain",
    )


def presign_put_upload(
    key: str,
    *,
    content_type: str = "video/mp4",
    size: int | None = None,
    ttl_seconds: int = 3600,
) -> dict:
    """Presigned PUT for direct browser upload to R2/S3."""
    del size  # R2: ContentLength in signature often breaks browser PUT
    bucket = _bucket()
    params: dict = {
        "Bucket": bucket,
        "Key": key,
        "ContentType": content_type,
    }
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


def configure_cors(origins: list[str]) -> dict:
    """Set CORS policy on the bucket so browsers can PUT/GET directly."""
    bucket = _bucket()
    cors_config = {
        "CORSRules": [
            {
                "AllowedOrigins": origins,
                "AllowedMethods": ["GET", "PUT", "HEAD"],
                "AllowedHeaders": ["*"],
                "ExposeHeaders": ["ETag"],
                "MaxAgeSeconds": 3600,
            }
        ]
    }
    client = _client()
    client.put_bucket_cors(Bucket=bucket, CORSConfiguration=cors_config)
    try:
        current = client.get_bucket_cors(Bucket=bucket)
        rules = current.get("CORSRules", [])
    except Exception:  # noqa: BLE001
        rules = cors_config["CORSRules"]
    return {"bucket": bucket, "cors_rules": rules}


def list_keys(prefix: str = "", limit: int = 100) -> list[dict]:
    bucket = _bucket()
    client = _client()
    out: list[dict] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents") or []:
            out.append(
                {
                    "key": obj["Key"],
                    "size_mb": round(obj["Size"] / (1024 * 1024), 1),
                    "modified": obj["LastModified"].isoformat(),
                }
            )
            if len(out) >= limit:
                return out
    return out


def probe_object(key: str) -> dict:
    """ffprobe a stored object via presigned URL — returns container/codec info."""
    import json as _json
    import subprocess

    from app.services.media_ffmpeg import ffprobe_binary

    url = presigned_get_url(f"s3://{_bucket()}/{key}")
    probe = ffprobe_binary()
    if not probe:
        return {"error": "ffprobe not available"}
    cmd = [
        probe,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    if proc.returncode != 0:
        return {"error": (proc.stderr or "")[:500], "returncode": proc.returncode}
    try:
        data = _json.loads(proc.stdout or "{}")
    except ValueError:
        return {"raw": (proc.stdout or "")[:1000]}
    streams = [
        {
            "type": s.get("codec_type"),
            "codec": s.get("codec_name"),
            "profile": s.get("profile"),
            "pix_fmt": s.get("pix_fmt"),
            "width": s.get("width"),
            "height": s.get("height"),
        }
        for s in data.get("streams", [])
    ]
    fmt = data.get("format", {})
    return {
        "format_name": fmt.get("format_name"),
        "duration": fmt.get("duration"),
        "size": fmt.get("size"),
        "streams": streams,
    }


def selftest() -> dict:
    """Diagnostic: report config presence and try a presign + put + delete."""
    info: dict = {
        "bucket": settings.S3_BUCKET.strip(),
        "endpoint_url": settings.S3_ENDPOINT_URL.strip(),
        "region": settings.S3_REGION.strip() or "auto",
        "has_access_key": bool(settings.S3_ACCESS_KEY.strip()),
        "has_secret_key": bool(settings.S3_SECRET_KEY.strip()),
        "enabled": object_storage_enabled(),
    }
    try:
        presign = presign_put_upload(
            f"selftest/probe-{uuid.uuid4().hex[:8]}.txt",
            content_type="text/plain",
        )
        info["presign_ok"] = True
        info["presign_host"] = urlparse(presign["upload_url"]).netloc
    except Exception as exc:  # noqa: BLE001
        info["presign_ok"] = False
        info["presign_error"] = str(exc)[:300]
    try:
        key = f"selftest/rw-{uuid.uuid4().hex[:8]}.txt"
        upload_bytes(key, b"ok", content_type="text/plain")
        delete_object(f"s3://{_bucket()}/{key}")
        info["read_write_ok"] = True
    except Exception as exc:  # noqa: BLE001
        info["read_write_ok"] = False
        info["read_write_error"] = str(exc)[:300]
    return info
