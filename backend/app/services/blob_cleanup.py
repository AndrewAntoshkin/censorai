"""Remove orphaned Vercel Blob objects; keep only in-flight analysis videos."""

from __future__ import annotations

import logging
from urllib.parse import urlparse, urlunparse

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import VideoFile
from app.models.upload_chunk_part import UploadChunkPart
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
        select(VideoFile.storage_path, VideoFile.status).where(
            VideoFile.storage_path.is_not(None),
            VideoFile.storage_path.like("http%"),
        )
    )
    keep_urls: set[str] = set()
    for url, status in rows.all():
        if not url:
            continue
        if status in {"analyzing", "uploaded", "processing"}:
            keep_urls.add(_normalize_blob_url(url))

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

    chunk_sessions = (await db.execute(select(UploadChunkSession.id))).all()
    chunk_parts_count = len((await db.execute(select(UploadChunkPart.session_id))).all())

    result = {
        "dry_run": dry_run,
        "blobs_total": len(blobs),
        "keep_in_flight": kept,
        "keep_urls_count": len(keep_urls),
        "delete_count": len(to_delete),
        "upload_chunk_sessions": len(chunk_sessions),
        "upload_chunk_parts_rows": chunk_parts_count,
    }

    if dry_run:
        return result

    delete_urls(to_delete)
    await db.execute(delete(UploadChunkPart))
    await db.execute(delete(UploadChunkSession))
    await db.flush()

    from app.services.blob_storage import reset_blob_write_cache

    reset_blob_write_cache()

    result["deleted"] = len(to_delete)
    result["chunk_parts_cleared"] = chunk_parts_count
    try:
        put_bytes("selftest/probe-after-cleanup.txt", b"ok", add_random_suffix=True)
        result["probe_ok"] = True
    except Exception as exc:
        result["probe_ok"] = False
        result["probe_note"] = str(exc)[:200]
    logger.info("Blob cleanup: deleted %d objects, kept %d in-flight", len(to_delete), kept)
    return result
