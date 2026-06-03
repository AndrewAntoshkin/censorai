"""Vercel Blob client upload (handleUpload protocol) on the FastAPI service."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any

from app.services.blob_storage import blob_enabled

logger = logging.getLogger(__name__)

_VIDEO_CONTENT_TYPES = [
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
    "application/octet-stream",
    "video/*",
]

_MAX_BLOB_BYTES = 500 * 1024 * 1024


def _read_write_token() -> str:
    from app.core.config import settings

    return (settings.BLOB_READ_WRITE_TOKEN or os.getenv("BLOB_READ_WRITE_TOKEN", "")).strip()


def _parse_store_id(token: str) -> str:
    parts = token.split("_")
    return parts[3] if len(parts) > 3 else ""


def generate_client_token_from_read_write_token(
    *,
    read_write_token: str,
    pathname: str,
    allowed_content_types: list[str] | None = None,
    maximum_size_in_bytes: int | None = None,
    add_random_suffix: bool | None = None,
    valid_until: int | None = None,
    on_upload_completed: dict[str, Any] | None = None,
) -> str:
    """Mirror @vercel/blob/client generateClientTokenFromReadWriteToken."""
    token = read_write_token.strip()
    store_id = _parse_store_id(token)
    if not store_id:
        raise RuntimeError("Invalid BLOB_READ_WRITE_TOKEN")

    if valid_until is None:
        valid_until = int((time.time() + 30) * 1000)

    args: dict[str, Any] = {"pathname": pathname, "validUntil": valid_until}
    if allowed_content_types is not None:
        args["allowedContentTypes"] = allowed_content_types
    if maximum_size_in_bytes is not None:
        args["maximumSizeInBytes"] = maximum_size_in_bytes
    if add_random_suffix is not None:
        args["addRandomSuffix"] = add_random_suffix
    if on_upload_completed is not None:
        args["onUploadCompleted"] = on_upload_completed

    payload = base64.b64encode(
        json.dumps(args, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    secured_key = hmac.new(
        token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    wrapped = base64.b64encode(f"{secured_key}.{payload}".encode("utf-8")).decode(
        "ascii"
    )
    return f"vercel_blob_client_{store_id}_{wrapped}"


def _on_before_generate_token(
    pathname: str,
    _client_payload: str | None,
    _multipart: bool,
) -> dict[str, Any]:
    del pathname, _client_payload, _multipart
    return {
        "allowedContentTypes": _VIDEO_CONTENT_TYPES,
        "maximumSizeInBytes": _MAX_BLOB_BYTES,
        "addRandomSuffix": True,
    }


async def handle_blob_upload_request(
    body: dict[str, Any],
    *,
    request_url: str,
    signature_header: str | None,
    raw_body: str | None = None,
) -> dict[str, Any]:
    del request_url, signature_header, raw_body
    if not blob_enabled():
        raise RuntimeError("BLOB_READ_WRITE_TOKEN not configured")

    event_type = body.get("type")
    rw_token = _read_write_token()

    if event_type == "blob.generate-client-token":
        payload = body.get("payload") or {}
        pathname = payload.get("pathname")
        if not pathname:
            raise RuntimeError("Missing pathname in token request")

        token_opts = _on_before_generate_token(
            pathname,
            payload.get("clientPayload"),
            bool(payload.get("multipart")),
        )
        valid_until = int(time.time() * 1000) + 60 * 60 * 1000

        client_token = generate_client_token_from_read_write_token(
            read_write_token=rw_token,
            pathname=pathname,
            valid_until=valid_until,
            allowed_content_types=token_opts["allowedContentTypes"],
            maximum_size_in_bytes=token_opts["maximumSizeInBytes"],
            add_random_suffix=token_opts["addRandomSuffix"],
        )
        return {"type": event_type, "clientToken": client_token}

    if event_type == "blob.upload-completed":
        return {"type": event_type, "response": "ok"}

    raise RuntimeError(f"Invalid event type: {event_type!r}")
