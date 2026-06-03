from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import CurrentAuth, require_auth_if_enabled
from app.models.project import Folder, Project, VideoFile
from app.services.access import apply_projects_scope, require_project_access
from app.schemas.project import (
    FolderCreate,
    FolderResponse,
    ProjectCreate,
    ProjectDetailResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project_buckets import UNASSIGNED_PROJECT_ID, is_system_project
from app.services.storage_service import storage_service

router = APIRouter(prefix=settings.route_prefix("/projects"), tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    user = auth.user if auth else None
    session = auth.session if auth else None
    # Demo seeding runs once at DB init (get_db -> ensure_database).
    stmt = (
        select(Project, func.count(VideoFile.id))
        .outerjoin(VideoFile, VideoFile.project_id == Project.id)
        .where(Project.id != UNASSIGNED_PROJECT_ID)
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
    )
    stmt = apply_projects_scope(stmt, user, session)
    rows = (await db.execute(stmt)).all()
    projects: list[ProjectResponse] = []
    for project, files_count in rows:
        resp = ProjectResponse.model_validate(project)
        resp.files_count = files_count
        projects.append(resp)
    return projects


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    user = auth.user if auth else None
    session = auth.session if auth else None
    from app.services.organization_service import effective_organization_id

    org_id = effective_organization_id(user, session) if user else None
    project = Project(
        name=data.name,
        owner_id=user.id if user else None,
        organization_id=org_id,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    user = auth.user if auth else None
    session = auth.session if auth else None
    if is_system_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    result = await db.execute(
        select(Project)
        .options(
            selectinload(Project.folders),
            selectinload(Project.files).selectinload(VideoFile.analysis),
        )
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    require_project_access(user, project, session)
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    user = auth.user if auth else None
    session = auth.session if auth else None
    if is_system_project(project_id):
        raise HTTPException(status_code=400, detail="Cannot update system project")
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    require_project_access(user, project, session)

    new_name = data.name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Project name cannot be empty")

    project.name = new_name
    await db.flush()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    user = auth.user if auth else None
    session = auth.session if auth else None
    if is_system_project(project_id):
        raise HTTPException(status_code=400, detail="Cannot delete system project")
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    require_project_access(user, project, session)

    await storage_service.delete_project_dir(str(project_id))
    await db.delete(project)
    await db.flush()


@router.post("/{project_id}/folders", response_model=FolderResponse, status_code=201)
async def create_folder(
    project_id: str,
    data: FolderCreate,
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    user = auth.user if auth else None
    session = auth.session if auth else None
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    require_project_access(user, project, session)

    folder = Folder(name=data.name, project_id=project_id)
    db.add(folder)
    await db.flush()
    await db.refresh(folder)
    return folder
