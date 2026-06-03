"""Finalize in-flight Replicate video analyses without blocking Neon."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import VideoFile
from app.schemas.analysis import GeminiAnalysisResult
from app.services.video_analysis_provider import poll_prediction

logger = logging.getLogger(__name__)


async def maybe_finish_analysis(
    video: VideoFile,
    db: AsyncSession,
    *,
    save_result,
) -> None:
    """Poll Replicate once, then persist under a short row lock.

    ``save_result(video, db, gemini_result)`` must set status=analyzed and
  analysis_id on success (see files._save_analysis_result).
    """
    if video.status != "analyzing" or not video.replicate_prediction_id:
        return

    prediction_id = video.replicate_prediction_id
    file_id = video.id

    # Do not hold FOR UPDATE or a Neon connection during the Replicate HTTP call.
    try:
        _status, result = await asyncio.to_thread(poll_prediction, prediction_id)
    except Exception as exc:
        await _handle_poll_error(video, db, file_id, exc)
        return

    if result is None:
        await _bump_progress(file_id, db)
        return

    await _persist_result(file_id, prediction_id, result, db, save_result=save_result)


async def _bump_progress(file_id: str, db: AsyncSession) -> None:
    row = await db.execute(
        select(VideoFile)
        .where(VideoFile.id == file_id)
        .with_for_update(skip_locked=True)
    )
    video = row.scalar_one_or_none()
    if not video or video.status != "analyzing" or video.analysis_id:
        return
    video.progress = min(98, (video.progress or 0) + 2)
    await db.flush()


async def _persist_result(
    file_id: str,
    prediction_id: str,
    result: GeminiAnalysisResult,
    db: AsyncSession,
    *,
    save_result,
) -> None:
    row = await db.execute(
        select(VideoFile)
        .where(VideoFile.id == file_id)
        .with_for_update(skip_locked=True)
    )
    video = row.scalar_one_or_none()
    if video is None:
        return

    if video.status != "analyzing":
        return
    if video.replicate_prediction_id != prediction_id:
        return

    if video.analysis_id:
        video.replicate_prediction_id = None
        video.status = "analyzed"
        video.progress = 100
        await db.flush()
        return

    try:
        from app.services.segmented_analysis import advance_after_segment

        if await advance_after_segment(
            video, db, result, save_merged=save_result
        ):
            return
        saved = await save_result(video, db, result)
        if saved is None:
            return
        video.replicate_prediction_id = None
    except Exception:
        logger.exception("Failed to save analysis for file %s; will retry on next poll", file_id)
        await db.rollback()
        # Leave status=analyzing and prediction_id so the next poll can re-fetch output.


async def _handle_poll_error(
    video: VideoFile,
    db: AsyncSession,
    file_id: str,
    exc: Exception,
) -> None:
    err = str(exc).lower()
    if (
        ("interrupted" in err or "code: pa" in err)
        and video.storage_path
        and (video.progress or 0) < 90
    ):
        path_ok = video.storage_path.startswith(("http://", "https://")) or Path(
            video.storage_path
        ).exists()
        if path_ok:
            row = await db.execute(
                select(VideoFile)
                .where(VideoFile.id == file_id)
                .with_for_update(skip_locked=True)
            )
            locked = row.scalar_one_or_none()
            if locked and locked.status == "analyzing":
                try:
                    from app.services.analysis_coverage import expected_duration_seconds

                    from app.services.video_analysis_provider import start_analysis

                    new_id = await asyncio.to_thread(
                        start_analysis,
                        locked.storage_path,
                        file_id=locked.id,
                        file_size=locked.size,
                        expected_duration_seconds=expected_duration_seconds(
                            locked.size or 0, locked.duration_seconds
                        ),
                    )
                    locked.replicate_prediction_id = new_id
                    locked.progress = min((locked.progress or 0) + 10, 85)
                    await db.flush()
                    return
                except Exception:
                    logger.exception("Retry failed for file %s", file_id)

    row = await db.execute(
        select(VideoFile)
        .where(VideoFile.id == file_id)
        .with_for_update(skip_locked=True)
    )
    locked = row.scalar_one_or_none()
    if not locked or locked.status != "analyzing":
        return

    logger.exception("Poll failed for file %s", file_id)
    locked.status = "error"
    locked.replicate_prediction_id = None
    await db.flush()
    from app.services.analysis_jobs import mark_job_failed

    await mark_job_failed(db, file_id, str(exc))
