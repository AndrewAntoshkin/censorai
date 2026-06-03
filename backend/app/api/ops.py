"""Operations metrics for super admins (stage 5)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import CurrentAuth, require_auth
from app.models.analysis_job import AnalysisJob, AnalysisJobStatus
from app.models.project import VideoFile
from app.services.organization_service import is_super_admin
from app.services.video_analysis_provider import get_video_provider_mode

router = APIRouter(prefix=settings.route_prefix("/ops"), tags=["ops"])


def _utc_naive_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("/metrics")
async def ops_metrics(
    auth: CurrentAuth = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    if not is_super_admin(auth.user):
        raise HTTPException(status_code=403, detail="Super admin only")

    video_counts = dict(
        (
            await db.execute(
                select(VideoFile.status, func.count())
                .group_by(VideoFile.status)
            )
        ).all()
    )

    job_counts = dict(
        (
            await db.execute(
                select(AnalysisJob.status, func.count()).group_by(AnalysisJob.status)
            )
        ).all()
    )

    analyzing = int(video_counts.get("analyzing", 0))
    queued = int(job_counts.get(AnalysisJobStatus.QUEUED.value, 0))
    failed_jobs = int(job_counts.get(AnalysisJobStatus.FAILED.value, 0))

    stale_cutoff = _utc_naive_now() - timedelta(hours=settings.ANALYSIS_STALE_JOB_HOURS)
    stale_row = await db.execute(
        select(func.count())
        .select_from(VideoFile)
        .where(
            VideoFile.status == "analyzing",
            VideoFile.updated_at < stale_cutoff,
        )
    )
    stale_analyzing = int(stale_row.scalar() or 0)

    return {
        "video_provider": get_video_provider_mode(),
        "object_storage": bool(settings.S3_BUCKET.strip() and settings.S3_ACCESS_KEY.strip()),
        "cascade_enabled": settings.ANALYSIS_CASCADE_ENABLED,
        "worker_poll_seconds": settings.ANALYSIS_WORKER_POLL_SECONDS,
        "videos_by_status": video_counts,
        "jobs_by_status": job_counts,
        "analyzing_count": analyzing,
        "queued_jobs": queued,
        "failed_jobs": failed_jobs,
        "stale_analyzing": stale_analyzing,
        "max_job_attempts": settings.ANALYSIS_JOB_MAX_ATTEMPTS,
    }
