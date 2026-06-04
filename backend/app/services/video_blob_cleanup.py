"""Remove Vercel Blob video files after analysis to free storage quota."""

from __future__ import annotations

import logging

from app.core.config import settings
from app.services.blob_storage import delete_blob_url, is_vercel_blob_url
from app.services.chunk_upload_service import is_chunk_session_path, release_chunk_session
from app.services.object_storage import delete_object, object_storage_enabled

logger = logging.getLogger(__name__)


def release_video_blob(storage_path: str | None) -> bool:
    """Delete processed video storage (Blob URL or postgres chunk session)."""
    if not settings.DELETE_BLOB_AFTER_ANALYSIS:
        return False
    if is_chunk_session_path(storage_path):
        return release_chunk_session(storage_path)
    if storage_path.startswith("s3://") and object_storage_enabled():
        try:
            delete_object(storage_path)
            logger.info("Released object storage: %s", storage_path[:96])
            return True
        except Exception:
            logger.exception("S3 delete failed: %s", storage_path[:96])
            return False
    if not is_vercel_blob_url(storage_path):
        return False
    if delete_blob_url(storage_path):
        logger.info("Released blob storage for analyzed video: %s", storage_path[:96])
        return True
    return False
