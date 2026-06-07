"""Lightweight search across projects and video files (reports)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import CurrentAuth, require_auth_if_enabled
from app.models.project import Project, VideoFile
from app.schemas.project import ProjectResponse, VideoFileResponse
from app.services.access import apply_files_scope, apply_projects_scope
from app.services.project_buckets import UNASSIGNED_PROJECT_ID

router = APIRouter(prefix=settings.route_prefix("/search"), tags=["search"])


class SearchResponse(BaseModel):
    projects: list[ProjectResponse]
    files: list[VideoFileResponse]


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(8, ge=1, le=25),
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    """Match projects and files by name within the caller's organization scope."""
    user = auth.user if auth else None
    session = auth.session if auth else None
    # Экранируем спецсимволы LIKE, чтобы «%» в запросе не ломал поиск.
    safe = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    term = f"%{safe}%"

    project_stmt = (
        select(Project)
        .where(Project.id != UNASSIGNED_PROJECT_ID)
        .where(Project.name.ilike(term, escape="\\"))
        .order_by(Project.created_at.desc())
        .limit(limit)
    )
    project_stmt = apply_projects_scope(project_stmt, user, session)
    projects = list((await db.execute(project_stmt)).scalars().all())

    file_stmt = (
        select(VideoFile)
        .where(VideoFile.name.ilike(term, escape="\\"))
        .order_by(VideoFile.created_at.desc())
        .limit(limit)
    )
    file_stmt = apply_files_scope(file_stmt, user, session)
    files = list((await db.execute(file_stmt)).scalars().all())

    return SearchResponse(projects=projects, files=files)
