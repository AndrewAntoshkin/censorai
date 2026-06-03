from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.organization import Organization, RegistrationCode
from app.models.user import AuthSession, User

FRAMECHECK_SLUG = "framecheck"


def normalize_registration_code(raw: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", raw.strip().upper())


def is_super_admin_email(email: str) -> bool:
    return email.strip().lower() == settings.SUPER_ADMIN_EMAIL.strip().lower()


def is_super_admin(user: User | None) -> bool:
    return user is not None and user.role == "super_admin"


def effective_organization_id(user: User, session: AuthSession | None) -> str | None:
    if user.organization_id is None:
        return None
    if is_super_admin(user) and session and session.active_organization_id:
        return session.active_organization_id
    return user.organization_id


async def get_organization_by_id(
    db: AsyncSession, organization_id: str
) -> Organization | None:
    return await db.get(Organization, organization_id)


async def resolve_registration_code(
    db: AsyncSession, raw_code: str
) -> Organization:
    normalized = normalize_registration_code(raw_code)
    if not normalized:
        raise ValueError("invalid_code")

    result = await db.execute(
        select(RegistrationCode)
        .options(selectinload(RegistrationCode.organization))
        .where(RegistrationCode.code == normalized, RegistrationCode.is_active.is_(True))
    )
    row = result.scalar_one_or_none()
    if row is None or row.organization is None:
        raise ValueError("invalid_code")
    return row.organization


async def list_organizations(db: AsyncSession) -> list[Organization]:
    result = await db.execute(select(Organization).order_by(Organization.name))
    return list(result.scalars().all())


async def ensure_framecheck_organization(db: AsyncSession) -> Organization:
    result = await db.execute(
        select(Organization).where(Organization.slug == FRAMECHECK_SLUG)
    )
    org = result.scalar_one_or_none()
    if org is not None:
        return org

    org = Organization(name=settings.FRAMECHECK_ORG_NAME, slug=FRAMECHECK_SLUG)
    db.add(org)
    await db.flush()
    await db.refresh(org)
    return org


async def ensure_registration_code(
    db: AsyncSession,
    *,
    organization: Organization,
    raw_code: str,
    label: str | None = None,
) -> RegistrationCode:
    normalized = normalize_registration_code(raw_code)
    result = await db.execute(
        select(RegistrationCode).where(RegistrationCode.code == normalized)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        if existing.organization_id != organization.id:
            raise ValueError("code_conflict")
        if not existing.is_active:
            existing.is_active = True
        if label:
            existing.label = label
        return existing

    code = RegistrationCode(
        code=normalized,
        organization_id=organization.id,
        label=label,
    )
    db.add(code)
    await db.flush()
    return code
