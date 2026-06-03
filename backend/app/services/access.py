"""Project and file access rules for multi-user workspaces."""

from __future__ import annotations

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.sql import Select

from app.core.config import settings
from app.models.project import Project, VideoFile
from app.models.user import AuthSession, User
from app.services.organization_service import effective_organization_id
from app.services.project_buckets import UNASSIGNED_PROJECT_ID


def auth_required() -> bool:
    return settings.AUTH_REQUIRED


def _effective_org(user: User | None, session: AuthSession | None) -> str | None:
    if user is None:
        return None
    return effective_organization_id(user, session)


def can_access_project(
    user: User | None, project: Project, session: AuthSession | None = None
) -> bool:
    if project.id == UNASSIGNED_PROJECT_ID:
        return False
    if user is None:
        return not auth_required()

    org_id = _effective_org(user, session)
    if project.organization_id is not None:
        return org_id is not None and project.organization_id == org_id

    if project.owner_id is None:
        return True
    return project.owner_id == user.id


def require_project_access(
    user: User | None, project: Project, session: AuthSession | None = None
) -> None:
    if not can_access_project(user, project, session):
        from fastapi import HTTPException

        if user is None and auth_required():
            raise HTTPException(status_code=401, detail="Authentication required")
        raise HTTPException(status_code=404, detail="Project not found")


def projects_list_filter(
    user: User | None, session: AuthSession | None = None
) -> ColumnElement[bool] | None:
    if user is None:
        if auth_required():
            return None
        return None

    org_id = _effective_org(user, session)
    if org_id is not None:
        return Project.organization_id == org_id

    return or_(Project.owner_id.is_(None), Project.owner_id == user.id)


def apply_projects_scope(
    stmt: Select, user: User | None, session: AuthSession | None = None
) -> Select:
    clause = projects_list_filter(user, session)
    if clause is not None:
        stmt = stmt.where(clause)
    return stmt


def apply_files_scope(
    stmt: Select, user: User | None, session: AuthSession | None = None
) -> Select:
    if user is None and not auth_required():
        return stmt
    if user is None:
        return stmt.where(False)

    org_id = _effective_org(user, session)
    if org_id is not None:
        visible = select(Project.id).where(Project.organization_id == org_id)
    else:
        visible = select(Project.id).where(
            or_(Project.owner_id.is_(None), Project.owner_id == user.id)
        )
    return stmt.where(VideoFile.project_id.in_(visible))
