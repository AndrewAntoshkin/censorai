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
    return bool(
        os.getenv("BLOB_READ_WRITE_TOKEN", "").strip()
        or (
            os.getenv("VERCEL_OIDC_TOKEN", "").strip()
            and os.getenv("BLOB_STORE_ID", "").strip()
        )
    )


def _normalize_store_id(store_id: str) -> str:
    return store_id.removeprefix("store_").strip()


def _store_id() -> str:
    explicit = os.getenv("BLOB_STORE_ID", "").strip()
    if explicit:
        return _normalize_store_id(explicit)

    token = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip()
    if token.startswith("vercel_blob_rw_"):
        rest = token[len("vercel_blob_rw_") :]
        return _normalize_store_id(rest.split("_", 1)[0])

    parts = token.split("_")
    if len(parts) > 3:
        return _normalize_store_id(parts[3])
    return ""


def _auth_headers() -> tuple[str, str]:
    """Return (authorization bearer value, store_id)."""
    store_id = _store_id()
    if not store_id:
        raise RuntimeError("BLOB_STORE_ID not configured")

    oidc = os.getenv("VERCEL_OIDC_TOKEN", "").strip()
    if oidc:
        return oidc, store_id

    token = os.getenv("BLOB_READ_WRITE_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BLOB_READ_WRITE_TOKEN not configured")
    return token, store_id


def put_bytes(
    pathname: str,
    data: bytes,
    *,
    content_type: str = "application/octet-stream",
    add_random_suffix: bool = False,
) -> dict:
    auth, store_id = _auth_headers()
    params = f"?pathname={quote(pathname, safe='')}"
    headers = {
        "authorization": f"Bearer {auth}",
        "x-api-version": API_VERSION,
        "x-content-length": str(len(data)),
        "x-vercel-blob-access": "public",
        "x-content-type": content_type,
        "x-add-random-suffix": "1" if add_random_suffix else "0",
        "x-allow-overwrite": "1",
        "x-vercel-blob-store-id": store_id,
    }
    url = f"{BLOB_API}/{params}"
    with httpx.Client(timeout=600) as client:
        response = client.put(url, content=data, headers=headers)
    if not response.is_success:
        logger.error(
            "Blob put failed %s %s: %s",
            response.status_code,
            pathname,
            response.text[:500],
        )
        response.raise_for_status()
    result = response.json()
    logger.info("Blob put %s -> %s (%d bytes)", pathname, result.get("url"), len(data))
    return result


def fetch_bytes(url: str) -> bytes:
    with httpx.Client(timeout=600, follow_redirects=True) as client:
        response = client.get(url)
    response.raise_for_status()
    return response.content
