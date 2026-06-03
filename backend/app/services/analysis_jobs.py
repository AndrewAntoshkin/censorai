from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.analysis_job import AnalysisJob, AnalysisJobStatus
from app.models.project import VideoFile


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def ensure_queued_job(db: AsyncSession, video_file_id: str) -> AnalysisJob:
    row = await db.execute(
        select(AnalysisJob).where(AnalysisJob.video_file_id == video_file_id)
    )
    job = row.scalar_one_or_none()
    if job is None:
        job = AnalysisJob(
            video_file_id=video_file_id,
            status=AnalysisJobStatus.QUEUED.value,
            attempts=0,
        )
        db.add(job)
    else:
        job.status = AnalysisJobStatus.QUEUED.value
        job.last_error = None
    await db.flush()
    return job


async def ensure_processing_job(db: AsyncSession, video_file_id: str) -> AnalysisJob:
    row = await db.execute(
        select(AnalysisJob).where(AnalysisJob.video_file_id == video_file_id)
    )
    job = row.scalar_one_or_none()
    if job is None:
        job = AnalysisJob(
            video_file_id=video_file_id,
            status=AnalysisJobStatus.PROCESSING.value,
            attempts=1,
        )
        db.add(job)
    else:
        job.status = AnalysisJobStatus.PROCESSING.value
        job.attempts = (job.attempts or 0) + 1
        job.last_error = None
    await db.flush()
    return job


async def mark_job_completed(db: AsyncSession, video_file_id: str) -> None:
    row = await db.execute(
        select(AnalysisJob).where(AnalysisJob.video_file_id == video_file_id)
    )
    job = row.scalar_one_or_none()
    if job is None:
        return
    job.status = AnalysisJobStatus.COMPLETED.value
    job.last_error = None
    await db.flush()


async def mark_job_failed(db: AsyncSession, video_file_id: str, error: str) -> None:
    row = await db.execute(
        select(AnalysisJob).where(AnalysisJob.video_file_id == video_file_id)
    )
    job = row.scalar_one_or_none()
    if job is None:
        job = AnalysisJob(
            video_file_id=video_file_id,
            status=AnalysisJobStatus.FAILED.value,
            attempts=1,
            last_error=error[:2000],
        )
        db.add(job)
    else:
        job.status = AnalysisJobStatus.FAILED.value
        job.last_error = error[:2000]
    await db.flush()


async def set_job_metadata(
    db: AsyncSession, video_file_id: str, metadata: dict
) -> None:
    row = await db.execute(
        select(AnalysisJob).where(AnalysisJob.video_file_id == video_file_id)
    )
    job = row.scalar_one_or_none()
    if job is None:
        return
    job.job_metadata = json.dumps(metadata, ensure_ascii=False)
    await db.flush()


async def get_job_metadata(db: AsyncSession, video_file_id: str) -> dict:
    row = await db.execute(
        select(AnalysisJob).where(AnalysisJob.video_file_id == video_file_id)
    )
    job = row.scalar_one_or_none()
    if not job or not job.job_metadata:
        return {}
    try:
        return json.loads(job.job_metadata)
    except json.JSONDecodeError:
        return {}


async def recover_stale_jobs(db: AsyncSession) -> int:
    """Re-queue stuck analyses (DLQ-style cap via max attempts)."""
    cutoff = _utc_naive_now() - timedelta(hours=settings.ANALYSIS_STALE_JOB_HOURS)
    max_attempts = settings.ANALYSIS_JOB_MAX_ATTEMPTS

    result = await db.execute(
        select(VideoFile, AnalysisJob)
        .outerjoin(AnalysisJob, AnalysisJob.video_file_id == VideoFile.id)
        .where(
            VideoFile.status == "analyzing",
            VideoFile.updated_at < cutoff,
        )
    )
    recovered = 0
    for video, job in result.all():
        attempts = job.attempts if job else 0
        if attempts >= max_attempts:
            video.status = "error"
            video.replicate_prediction_id = None
            if job:
                await mark_job_failed(db, video.id, "Max analysis attempts exceeded (stale)")
            continue

        video.replicate_prediction_id = None
        video.progress = max(video.progress or 0, 10)
        if job:
            job.status = AnalysisJobStatus.QUEUED.value
            job.last_error = "Recovered from stale processing state"
        recovered += 1
    if recovered:
        await db.flush()
    return recovered
