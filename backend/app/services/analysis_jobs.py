from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_job import AnalysisJob, AnalysisJobStatus


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
