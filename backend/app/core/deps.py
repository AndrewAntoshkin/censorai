from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import AuthSession, User
from app.services.auth_service import SESSION_COOKIE, get_auth_for_token


@dataclass
class CurrentAuth:
    user: User
    session: AuthSession


async def get_optional_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CurrentAuth | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    pair = await get_auth_for_token(db, token)
    if pair is None:
        return None
    user, session = pair
    return CurrentAuth(user=user, session=session)


async def get_optional_user(
    auth: CurrentAuth | None = Depends(get_optional_auth),
) -> User | None:
    return auth.user if auth else None


async def require_user(
    auth: CurrentAuth | None = Depends(get_optional_auth),
) -> User:
    if auth is not None:
        return auth.user
    if settings.AUTH_REQUIRED:
        raise HTTPException(status_code=401, detail="Authentication required")
    raise HTTPException(status_code=401, detail="Sign in required")


async def require_auth(
    auth: CurrentAuth | None = Depends(get_optional_auth),
) -> CurrentAuth:
    if auth is not None:
        return auth
    if settings.AUTH_REQUIRED:
        raise HTTPException(status_code=401, detail="Authentication required")
    raise HTTPException(status_code=401, detail="Sign in required")


async def require_auth_if_enabled(
    auth: CurrentAuth | None = Depends(get_optional_auth),
) -> CurrentAuth | None:
    if settings.AUTH_REQUIRED and auth is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return auth
