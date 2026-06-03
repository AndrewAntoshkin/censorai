"""Single round-trip for home/sidebar data (fewer serverless cold starts)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import CurrentAuth, require_auth_if_enabled
from app.models.project import Project, VideoFile
from app.schemas.project import ProjectResponse, VideoFileResponse
from app.services.access import apply_files_scope, apply_projects_scope
from app.services.project_buckets import UNASSIGNED_PROJECT_ID

router = APIRouter(prefix=settings.route_prefix("/workspace"), tags=["workspace"])

WORKING_STATUSES = frozenset({"uploading", "uploaded", "analyzing"})


class WorkspaceSummaryResponse(BaseModel):
    projects: list[ProjectResponse]
    recent_files: list[VideoFileResponse]
    in_progress_count: int


@router.get("/summary", response_model=WorkspaceSummaryResponse)
async def workspace_summary(
    recent_limit: int = Query(24, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    user = auth.user if auth else None
    session = auth.session if auth else None

    project_stmt = (
        select(Project, func.count(VideoFile.id))
        .outerjoin(VideoFile, VideoFile.project_id == Project.id)
        .where(Project.id != UNASSIGNED_PROJECT_ID)
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
    )
    project_stmt = apply_projects_scope(project_stmt, user, session)
    project_rows = (await db.execute(project_stmt)).all()
    projects: list[ProjectResponse] = []
    for project, files_count in project_rows:
        resp = ProjectResponse.model_validate(project)
        resp.files_count = files_count
        projects.append(resp)

    recent_stmt = (
        select(VideoFile)
        .order_by(VideoFile.created_at.desc())
        .limit(recent_limit)
    )
    recent_stmt = apply_files_scope(recent_stmt, user, session)
    recent_files = list((await db.execute(recent_stmt)).scalars().all())

    in_progress = sum(
        1 for f in recent_files if (f.status or "").lower() in WORKING_STATUSES
    )

    return WorkspaceSummaryResponse(
        projects=projects,
        recent_files=recent_files,
        in_progress_count=in_progress,
    )
