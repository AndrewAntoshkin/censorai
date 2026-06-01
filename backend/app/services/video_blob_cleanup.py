"""Remove Vercel Blob video files after analysis to free storage quota."""

from __future__ import annotations

import logging

from app.core.config import settings
from app.services.blob_storage import delete_blob_url, is_vercel_blob_url

logger = logging.getLogger(__name__)


def release_video_blob(storage_path: str | None) -> bool:
    """Delete a processed video from Blob. Returns True if a blob URL was removed."""
    if not settings.DELETE_BLOB_AFTER_ANALYSIS:
        return False
    if not is_vercel_blob_url(storage_path):
        return False
    if delete_blob_url(storage_path):
        logger.info("Released blob storage for analyzed video: %s", storage_path[:96])
        return True
    return False
