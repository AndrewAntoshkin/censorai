"""Internal project buckets (e.g. uploads without a user-selected project)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project

UNASSIGNED_PROJECT_ID = "__unassigned__"
UNASSIGNED_PROJECT_NAME = "__unassigned__"


def is_system_project(project_id: str | None) -> bool:
    return project_id == UNASSIGNED_PROJECT_ID


async def ensure_unassigned_project(db: AsyncSession) -> str:
    result = await db.execute(
        select(Project).where(Project.id == UNASSIGNED_PROJECT_ID)
    )
    if result.scalar_one_or_none():
        return UNASSIGNED_PROJECT_ID

    project = Project(id=UNASSIGNED_PROJECT_ID, name=UNASSIGNED_PROJECT_NAME)
    db.add(project)
    await db.flush()
    return UNASSIGNED_PROJECT_ID


async def resolve_project_id(db: AsyncSession, project_id: str | None) -> str:
    if project_id and not is_system_project(project_id):
        result = await db.execute(select(Project).where(Project.id == project_id))
        if not result.scalar_one_or_none():
            raise ValueError(f"Project not found: {project_id}")
        return project_id

    await ensure_unassigned_project(db)
    return UNASSIGNED_PROJECT_ID
