"""Internal project buckets (e.g. uploads without a user-selected project)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.models.user import AuthSession, User
from app.services.organization_service import effective_organization_id

UNASSIGNED_PROJECT_ID = "__unassigned__"
UNASSIGNED_PROJECT_NAME = "__unassigned__"
INBOX_PROJECT_NAME = "Входящие"


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


async def get_or_create_inbox_project(
    db: AsyncSession, user: User, session: AuthSession | None = None
) -> str:
    """Default target when user uploads from the header without picking a project."""
    org_id = effective_organization_id(user, session)
    if org_id is None:
        await ensure_unassigned_project(db)
        return UNASSIGNED_PROJECT_ID

    row = await db.execute(
        select(Project).where(
            Project.organization_id == org_id,
            Project.name == INBOX_PROJECT_NAME,
        )
    )
    project = row.scalar_one_or_none()
    if project is None:
        project = Project(
            name=INBOX_PROJECT_NAME,
            organization_id=org_id,
            owner_id=user.id,
        )
        db.add(project)
        await db.flush()
    return project.id


async def resolve_project_id(
    db: AsyncSession,
    project_id: str | None,
    *,
    user: User | None = None,
    session: AuthSession | None = None,
) -> str:
    if project_id and not is_system_project(project_id):
        result = await db.execute(select(Project).where(Project.id == project_id))
        if not result.scalar_one_or_none():
            raise ValueError(f"Project not found: {project_id}")
        return project_id

    if user is not None:
        return await get_or_create_inbox_project(db, user, session)

    await ensure_unassigned_project(db)
    return UNASSIGNED_PROJECT_ID
