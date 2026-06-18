"""Background analysis polling — does not depend on frontend GET requests."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.core.db_init import ensure_database
from app.models.analysis_job import AnalysisJob, AnalysisJobStatus
from app.models.project import VideoFile
from app.services.analysis_jobs import recover_stale_jobs

logger = logging.getLogger(__name__)

MAX_FILES_PER_TICK = 50
MAX_QUEUED_KICKOFFS = 10


async def run_analysis_poll_cycle() -> dict:
    """Poll in-flight analyses, drain queued jobs, recover stale work."""
    await ensure_database()

    processed = 0
    errors = 0
    recovered = 0
    queued_started = 0
    pending = 0

    async with async_session_factory() as db:
        recovered = await recover_stale_jobs(db)
        queued_started = await _process_queued_kickoffs(db)
        await db.commit()

        result = await db.execute(
            select(VideoFile.id)
            .where(VideoFile.status == "analyzing")
            .order_by(VideoFile.updated_at.asc())
            .limit(MAX_FILES_PER_TICK)
        )
        file_ids = list(result.scalars().all())
        pending = len(file_ids)

        for file_id in file_ids:
            try:
                await _process_one(file_id, db)
                await db.commit()
                processed += 1
            except Exception:
                errors += 1
                await db.rollback()
                logger.exception("Worker failed for file %s", file_id)

    stats = {
        "processed": processed,
        "errors": errors,
        "recovered": recovered,
        "queued_started": queued_started,
        "pending": pending,
    }
    if pending or recovered or queued_started:
        logger.info("Poll tick: %s", stats)
    return stats


async def _process_queued_kickoffs(db: AsyncSession) -> int:
    """Start analysis for queued uploads; one worker wins per row (SKIP LOCKED)."""
    from app.api.files import _kickoff_analysis

    candidates = await db.execute(
        select(VideoFile.id)
        .join(AnalysisJob, AnalysisJob.video_file_id == VideoFile.id)
        .where(
            AnalysisJob.status == AnalysisJobStatus.QUEUED.value,
            VideoFile.status.in_(["uploaded", "analyzing"]),
            VideoFile.replicate_prediction_id.is_(None),
        )
        .order_by(AnalysisJob.updated_at.asc())
        .limit(MAX_QUEUED_KICKOFFS)
    )
    started = 0
    for file_id in candidates.scalars().all():
        row = await db.execute(
            select(VideoFile)
            .where(VideoFile.id == file_id)
            .with_for_update(skip_locked=True)
        )
        video = row.scalar_one_or_none()
        if video is None:
            continue
        if video.replicate_prediction_id or video.status not in ("uploaded", "analyzing"):
            continue
        job_row = await db.execute(
            select(AnalysisJob).where(AnalysisJob.video_file_id == file_id)
        )
        job = job_row.scalar_one_or_none()
        if job is None or job.status != AnalysisJobStatus.QUEUED.value:
            continue
        try:
            await _kickoff_analysis(video, db, from_queue=True)
            started += 1
        except Exception:
            logger.exception("Queued kickoff failed for %s", file_id)
    return started


async def _process_one(file_id: str, db: AsyncSession) -> None:
    from app.api.files import _maybe_finish_analysis

    # IMPORTANT: do NOT take a FOR UPDATE row lock here. The direct-Gemini path
    # claims the same row in a separate session via skip_locked; holding a lock
    # here makes that inner claim see the row as locked and silently no-op, so a
    # segmented file never advances under the autonomous poller (it only moved
    # when the frontend's lock-free poll_direct path drove it). Mirror that
    # lock-free read; concurrency is handled by the inner claim and persist.
    row = await db.execute(select(VideoFile).where(VideoFile.id == file_id))
    video = row.scalar_one_or_none()
    if video is None or video.status != "analyzing":
        return
    await _maybe_finish_analysis(video, db)
