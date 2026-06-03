"""Prepare video storage paths so Replicate can fetch files (Blob URL or signed media)."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.project import VideoFile
from app.services.blob_storage import blob_enabled, put_bytes

logger = logging.getLogger(__name__)


def effective_size_bytes(storage_path: str, file_size: int | None) -> int:
    if storage_path.startswith(("http://", "https://")):
        return file_size or 0
    path = Path(storage_path)
    if path.exists():
        return max(file_size or 0, path.stat().st_size)
    return file_size or 0


def public_api_is_localhost() -> bool:
    host = (urlparse(settings.public_api_base_url).hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "0.0.0.0", ""}


def needs_public_video_url(storage_path: str, file_size: int | None) -> bool:
    if storage_path.startswith(("http://", "https://", "s3://")):
        return False
    size_mb = effective_size_bytes(storage_path, file_size) / (1024 * 1024)
    return size_mb > settings.INLINE_VIDEO_MAX_MB


async def ensure_public_video_url(video: VideoFile, db: AsyncSession) -> None:
    """Upload large local files to Blob or fail with a clear dev hint."""
    path = video.storage_path or ""
    if not path or path.startswith(("http://", "https://")):
        return

    if not needs_public_video_url(path, video.size):
        return

    if blob_enabled():
        local = Path(path)
        if not local.exists():
            raise FileNotFoundError(f"Video not found: {path}")

        ext = local.suffix.lstrip(".") or "mp4"
        blob_path = f"videos/{video.id}.{ext}"
        logger.info("Uploading %.1f MB to Blob for Replicate", local.stat().st_size / (1024**2))

        def _put() -> str:
            result = put_bytes(
                blob_path,
                local.read_bytes(),
                content_type="video/mp4",
                add_random_suffix=False,
            )
            url = result.get("url")
            if not url:
                raise RuntimeError("Blob upload returned no URL")
            return url

        video.storage_path = await asyncio.to_thread(_put)
        await db.flush()
        return

    if public_api_is_localhost():
        limit = settings.INLINE_VIDEO_MAX_MB
        raise RuntimeError(
            f"Видео больше {limit} МБ: для локальной разработки добавьте в backend/.env "
            "BLOB_READ_WRITE_TOKEN (Vercel Blob) или PUBLIC_API_BASE_URL с публичным URL "
            "(например ngrok). Без этого Replicate не сможет скачать файл с localhost."
        )
