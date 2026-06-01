"""Server-side Vercel Blob uploads (no browser → blob CDN)."""

from __future__ import annotations

import logging
import os
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

BLOB_API = "https://vercel.com/api/blob"
API_VERSION = "12"


def blob_enabled() -> bool:
    return bool(os.getenv("BLOB_READ_WRITE_TOKEN", "").strip())


def _token() -> str:
    token = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BLOB_READ_WRITE_TOKEN not configured")
    return token


def _store_id(token: str) -> str:
    parts = token.split("_")
    return parts[3] if len(parts) > 3 else ""


def put_bytes(
    pathname: str,
    data: bytes,
    *,
    content_type: str = "application/octet-stream",
    add_random_suffix: bool = False,
) -> dict:
    token = _token()
    store_id = _store_id(token)
    params = f"?pathname={quote(pathname, safe='')}"
    headers = {
        "authorization": f"Bearer {token}",
        "x-api-version": API_VERSION,
        "x-content-length": str(len(data)),
        "x-vercel-blob-access": "public",
        "x-content-type": content_type,
        "x-add-random-suffix": "1" if add_random_suffix else "0",
        "x-allow-overwrite": "1",
        "x-vercel-blob-store-id": store_id,
    }
    with httpx.Client(timeout=600) as client:
        response = client.put(f"{BLOB_API}/{params}", content=data, headers=headers)
    response.raise_for_status()
    result = response.json()
    logger.info("Blob put %s -> %s (%d bytes)", pathname, result.get("url"), len(data))
    return result


def fetch_bytes(url: str) -> bytes:
    with httpx.Client(timeout=600, follow_redirects=True) as client:
        response = client.get(url)
    response.raise_for_status()
    return response.content


def public_blob_url(pathname: str) -> str:
    """Public URL for a fixed pathname (addRandomSuffix=false)."""
    store_id = _store_id(_token())
    return f"https://{store_id}.public.blob.vercel-storage.com/{pathname}"
