from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.organization import Organization
from app.models.user import AuthSession, User
from app.services.organization_service import (
    ensure_framecheck_organization,
    is_super_admin_email,
    resolve_registration_code,
)

SESSION_COOKIE = "fc_session"
SESSION_DAYS = 30


def _utc_naive(dt: datetime | None = None) -> datetime:
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    normalized = email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized))
    return result.scalar_one_or_none()


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str,
    registration_code: str,
) -> User:
    normalized = email.strip().lower()
    existing = await get_user_by_email(db, normalized)
    if existing:
        raise ValueError("email_taken")

    try:
        organization = await resolve_registration_code(db, registration_code)
    except ValueError as exc:
        if str(exc) == "invalid_code":
            raise ValueError("invalid_code") from exc
        raise

    role = "super_admin" if is_super_admin_email(normalized) else "member"
    if role == "super_admin":
        organization = await ensure_framecheck_organization(db)

    user = User(
        email=normalized,
        password_hash=hash_password(password),
        display_name=display_name.strip(),
        organization_id=organization.id,
        role=role,
    )
    db.add(user)
    await db.flush()
    result = await db.execute(
        select(User)
        .options(selectinload(User.organization))
        .where(User.id == user.id)
    )
    return result.scalar_one()


async def authenticate_user(db: AsyncSession, *, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None

    normalized = email.strip().lower()
    if is_super_admin_email(normalized) and user.role != "super_admin":
        user.role = "super_admin"
        framecheck = await ensure_framecheck_organization(db)
        user.organization_id = framecheck.id
        await db.flush()
    result = await db.execute(
        select(User)
        .options(selectinload(User.organization))
        .where(User.id == user.id)
    )
    return result.scalar_one()


async def create_session(db: AsyncSession, user: User) -> tuple[str, AuthSession]:
    token = new_session_token()
    session = AuthSession(
        user_id=user.id,
        token_hash=_hash_token(token),
        expires_at=_utc_naive() + timedelta(days=SESSION_DAYS),
        active_organization_id=user.organization_id,
    )
    db.add(session)
    await db.flush()
    return token, session


async def get_auth_for_token(
    db: AsyncSession, token: str | None
) -> tuple[User, AuthSession] | None:
    if not token:
        return None
    now = _utc_naive()
    result = await db.execute(
        select(User, AuthSession)
        .join(AuthSession, AuthSession.user_id == User.id)
        .options(selectinload(User.organization))
        .where(
            AuthSession.token_hash == _hash_token(token),
            AuthSession.expires_at > now,
        )
    )
    row = result.first()
    if row is None:
        return None
    return row[0], row[1]


async def get_user_for_token(db: AsyncSession, token: str | None) -> User | None:
    pair = await get_auth_for_token(db, token)
    return pair[0] if pair else None


async def revoke_session(db: AsyncSession, token: str | None) -> None:
    if not token:
        return
    await db.execute(
        delete(AuthSession).where(AuthSession.token_hash == _hash_token(token))
    )


async def revoke_all_sessions(db: AsyncSession, user_id: str) -> None:
    await db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))


def session_cookie_kwargs() -> dict:
    secure = bool(
        settings.PUBLIC_API_BASE_URL.startswith("https://")
        or __import__("os").getenv("VERCEL")
    )
    return {
        "key": SESSION_COOKIE,
        "httponly": True,
        "samesite": "lax",
        "path": "/",
        "max_age": SESSION_DAYS * 24 * 3600,
        "secure": secure,
    }
