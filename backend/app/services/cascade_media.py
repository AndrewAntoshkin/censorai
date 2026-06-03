"""Resolve a local filesystem path for ffmpeg scene detection (incl. S3)."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_local_video_path(storage_path: str) -> tuple[str, Path | None]:
    """Return path for ffmpeg and optional temp file to delete after use."""
    if not storage_path:
        return "", None

    if storage_path.startswith("s3://"):
        from app.services.object_storage import download_object_to_tempfile

        temp = download_object_to_tempfile(storage_path)
        return str(temp), temp

    if storage_path.startswith(("http://", "https://")):
        return "", None

    path = Path(storage_path)
    if path.is_file():
        return str(path), None

    logger.warning("Scene pre-pass skipped — file missing: %s", storage_path)
    return "", None


def cleanup_temp_path(temp: Path | None) -> None:
    if temp is None:
        return
    try:
        temp.unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Failed to remove temp scene file %s: %s", temp, exc)
