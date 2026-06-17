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


# Substrings that mean "try again later", not "this file is broken". These
# come from shared serverless resources (disk/network/model capacity), so the
# same file usually succeeds on a later attempt once the pressure clears.
_TRANSIENT_ERROR_MARKERS = (
    "no space left on device",
    "errno 28",
    "недостаточно места",
    "insufficient_tmp_space",
    "timeout",
    "timed out",
    "temporarily unavailable",
    "rate limit",
    "rate_limit",
    "resource exhausted",
    "resource_exhausted",
    "connection reset",
    "connection aborted",
    "connection error",
    "interrupted",
    "code: pa",
    "503",
    "502",
    "500 internal",
    "deadline exceeded",
    "remoteprotocolerror",
    "read timed out",
)

# Substrings that mean "this content/file will never pass" — fail fast, no retry.
_PERMANENT_ERROR_MARKERS = (
    "block_reason",
    "blocked the input",
    "prohibited",
    "no storage path",
    "file has no storage",
    "not found",
    "filenotfound",
)


def is_transient_analysis_error(error: str | Exception) -> bool:
    """True if the error is worth an automatic retry (shared-resource pressure)."""
    msg = str(error).lower()
    if any(marker in msg for marker in _PERMANENT_ERROR_MARKERS):
        return False
    return any(marker in msg for marker in _TRANSIENT_ERROR_MARKERS)


async def requeue_transient_failure(
    db: AsyncSession, video_file_id: str, error: str, *, count_attempt: bool = True
) -> bool:
    """Re-queue a transiently-failed analysis instead of marking it errored.

    Returns True if re-queued (caller should keep status=analyzing and reset the
    prediction marker to pending). Returns False once attempts are exhausted, so
    the caller falls through to a real ``error`` state.
    """
    row = await db.execute(
        select(AnalysisJob).where(AnalysisJob.video_file_id == video_file_id)
    )
    job = row.scalar_one_or_none()
    max_attempts = settings.ANALYSIS_JOB_MAX_ATTEMPTS
    if job is None:
        job = AnalysisJob(
            video_file_id=video_file_id,
            status=AnalysisJobStatus.QUEUED.value,
            attempts=1,
            last_error=f"Transient, will retry: {error[:1500]}",
        )
        db.add(job)
        await db.flush()
        return True

    attempts = job.attempts or 0
    if count_attempt and attempts >= max_attempts:
        return False
    if count_attempt:
        job.attempts = attempts + 1
    job.status = AnalysisJobStatus.QUEUED.value
    job.last_error = (
        f"Transient (attempt {job.attempts}/{max_attempts}), auto-retry: {error[:1500]}"
    )
    await db.flush()
    return True


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
