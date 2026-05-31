"""Resolve DATABASE_URL from Vercel/Neon env vars before Settings loads."""

import logging
import os

logger = logging.getLogger(__name__)


def _normalize_async_url(raw: str) -> str:
    url = raw.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    return url


def _normalize_sync_url(raw: str) -> str:
    url = raw.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def resolve_database_env() -> None:
    """Map POSTGRES_URL / Neon / Vercel Postgres vars to SQLAlchemy URLs."""
    raw = (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or os.getenv("POSTGRES_URL_NON_POOLING")
        or os.getenv("POSTGRES_PRISMA_URL")
        or os.getenv("STORAGE_URL")
        or ""
    ).strip()
    if not raw:
        return

    os.environ["DATABASE_URL"] = _normalize_async_url(raw)
    os.environ["DATABASE_URL_SYNC"] = _normalize_sync_url(raw)
    logger.info("Database URL resolved from environment (Postgres)")


def is_ephemeral_sqlite() -> bool:
    url = os.getenv("DATABASE_URL", "")
    return "sqlite" in url and "/tmp/" in url
