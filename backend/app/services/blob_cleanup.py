"""Remove orphaned Vercel Blob objects; keep analyzed video URLs only."""

from __future__ import annotations

import json
import logging
from urllib.parse import urlparse, urlunparse

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import VideoFile
from app.models.upload_session import UploadChunkSession
from app.services.blob_storage import blob_enabled, delete_urls, list_all_blobs, put_bytes

logger = logging.getLogger(__name__)

DELETE_PREFIXES = ("chunks/", "selftest/")


def _normalize_blob_url(url: str) -> str:
    parsed = urlparse(url.strip())
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


async def prune_blob_storage(db: AsyncSession, *, dry_run: bool = False) -> dict:
    if not blob_enabled():
        raise RuntimeError("BLOB_READ_WRITE_TOKEN not configured")

    rows = await db.execute(
        select(VideoFile.storage_path).where(
            VideoFile.status == "analyzed",
            VideoFile.storage_path.is_not(None),
            VideoFile.storage_path.like("http%"),
        )
    )
    keep_urls = {_normalize_blob_url(url) for (url,) in rows.all() if url}

    blobs = list_all_blobs()
    to_delete: list[str] = []
    kept = 0
    for blob in blobs:
        url = blob.get("url") or ""
        pathname = blob.get("pathname") or ""
        if not url:
            continue
        if any(pathname.startswith(p) for p in DELETE_PREFIXES):
            to_delete.append(url)
            continue
        if _normalize_blob_url(url) in keep_urls:
            kept += 1
            continue
        to_delete.append(url)

    chunk_count = (
        await db.execute(select(UploadChunkSession.id))
    ).all()

    result = {
        "dry_run": dry_run,
        "blobs_total": len(blobs),
        "keep_analyzed": kept,
        "keep_urls_count": len(keep_urls),
        "delete_count": len(to_delete),
        "upload_chunk_sessions": len(chunk_count),
    }

    if dry_run:
        return result

    delete_urls(to_delete)
    if chunk_count:
        await db.execute(delete(UploadChunkSession))
        await db.commit()

    result["deleted"] = len(to_delete)
    try:
        put_bytes("selftest/probe-after-cleanup.txt", b"ok", add_random_suffix=True)
        result["probe_ok"] = True
    except Exception as e:
        result["probe_ok"] = False
        result["probe_note"] = str(e)[:200]
    logger.info("Blob cleanup: deleted %d objects, kept %d", len(to_delete), kept)
    return result
