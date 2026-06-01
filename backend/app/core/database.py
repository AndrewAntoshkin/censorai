from collections.abc import AsyncGenerator

import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings

connect_args: dict = {}
engine_kwargs: dict = {}

_uses_null_pool = False
if "sqlite" in settings.DATABASE_URL:
    connect_args = {"check_same_thread": False}
elif "postgres" in settings.DATABASE_URL:
    connect_args = {"ssl": "require", "statement_cache_size": 0}
    if os.getenv("VERCEL"):
        engine_kwargs["poolclass"] = NullPool
        _uses_null_pool = True

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    # With NullPool every request opens a fresh connection, so pre-ping just
    # adds a wasted SELECT 1 round-trip to Neon. Only pre-ping when pooling.
    pool_pre_ping=not _uses_null_pool,
    **engine_kwargs,
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    from app.core.db_init import ensure_database

    await ensure_database()
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
