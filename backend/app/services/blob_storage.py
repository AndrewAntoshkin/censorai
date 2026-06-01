"""Server-side Vercel Blob uploads via the official vercel_blob SDK.

The previous hand-rolled HTTP client targeted the wrong endpoint
(https://vercel.com/api/blob) and every upload failed with 500. We now delegate
to the maintained vercel_blob package, which uses the correct Blob API base URL,
version and headers, and only needs BLOB_READ_WRITE_TOKEN.
"""

from __future__ import annotations

import logging
import os

import httpx
import vercel_blob

logger = logging.getLogger(__name__)

# Use multipart for larger payloads (merged videos) to avoid single-request limits.
_MULTIPART_THRESHOLD = 8 * 1024 * 1024


def blob_enabled() -> bool:
    return bool(os.getenv("BLOB_READ_WRITE_TOKEN", "").strip())


def put_bytes(
    pathname: str,
    data: bytes,
    *,
    content_type: str = "application/octet-stream",
    add_random_suffix: bool = False,
) -> dict:
    """Upload bytes to Vercel Blob (public access). Returns API response with 'url'.

    content_type is accepted for call-site compatibility; vercel_blob infers the
    MIME type from the pathname extension (parts -> octet-stream, *.mp4 -> video/mp4).
    """
    options = {
        "addRandomSuffix": "true" if add_random_suffix else "false",
        "allowOverwrite": "true",
    }
    multipart = len(data) > _MULTIPART_THRESHOLD
    result = vercel_blob.put(pathname, data, options, multipart=multipart)
    url = result.get("url") if isinstance(result, dict) else None
    if not url:
        raise RuntimeError(f"Blob put returned no url for {pathname}: {result!r}")
    logger.info("Blob put %s -> %s (%d bytes)", pathname, url, len(data))
    return result


def fetch_bytes(url: str) -> bytes:
    with httpx.Client(timeout=600, follow_redirects=True) as client:
        response = client.get(url)
    response.raise_for_status()
    return response.content


def list_all_blobs() -> list[dict]:
    """List every object in the store (paginated)."""
    items: list[dict] = []
    cursor: str | None = None
    while True:
        options: dict = {"limit": 1000, "mode": "expanded"}
        if cursor:
            options["cursor"] = cursor
        page = vercel_blob.list(options, timeout=120)
        items.extend(page.get("blobs") or [])
        if not page.get("hasMore"):
            break
        cursor = page.get("cursor")
        if not cursor:
            break
    return items


def delete_urls(urls: list[str]) -> None:
    if not urls:
        return
    batch_size = 50
    for i in range(0, len(urls), batch_size):
        vercel_blob.delete(urls[i : i + batch_size], timeout=120)
