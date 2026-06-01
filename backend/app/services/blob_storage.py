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


def is_vercel_blob_url(url: str | None) -> bool:
    if not url:
        return False
    return "blob.vercel-storage.com" in url or ".public.blob.vercel-storage.com" in url


def delete_urls(urls: list[str]) -> None:
    """Delete Blob objects by public URL. No-op when Blob is not configured."""
    if not blob_enabled() or not urls:
        return
    batch_size = 50
    for i in range(0, len(urls), batch_size):
        batch = [u for u in urls[i : i + batch_size] if is_vercel_blob_url(u)]
        if not batch:
            continue
        try:
            vercel_blob.delete(batch, timeout=120)
            logger.info("Deleted %d blob object(s)", len(batch))
        except Exception:
            logger.exception("Blob delete failed for batch of %d url(s)", len(batch))


def delete_blob_url(url: str | None) -> bool:
    if not blob_enabled() or not is_vercel_blob_url(url):
        return False
    try:
        vercel_blob.delete([url], timeout=120)
        logger.info("Deleted blob: %s", (url or "")[:96])
        return True
    except Exception:
        logger.exception("Blob delete failed: %s", (url or "")[:96])
        return False
