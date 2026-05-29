from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.project import Folder, Project, VideoFile
from app.schemas.project import (
    FolderCreate,
    FolderResponse,
    ProjectCreate,
    ProjectDetailResponse,
    ProjectResponse,
)
from app.services.storage_service import storage_service

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Project, func.count(VideoFile.id))
        .outerjoin(VideoFile, VideoFile.project_id == Project.id)
        .group_by(Project.id)
        .order_by(Project.created_at.desc())
    )
    rows = (await db.execute(stmt)).all()
    projects: list[ProjectResponse] = []
    for project, files_count in rows:
        resp = ProjectResponse.model_validate(project)
        resp.files_count = files_count
        projects.append(resp)
    return projects


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(name=data.name)
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
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
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    await storage_service.delete_project_dir(str(project_id))
    await db.delete(project)
    await db.flush()


@router.post("/{project_id}/folders", response_model=FolderResponse, status_code=201)
async def create_folder(
    project_id: str, data: FolderCreate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    folder = Folder(name=data.name, project_id=project_id)
    db.add(folder)
    await db.flush()
    await db.refresh(folder)
    return folder
