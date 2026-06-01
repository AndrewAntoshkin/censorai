"""Resolve DATABASE_URL from Vercel/Neon env vars before Settings loads."""

import logging
import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

logger = logging.getLogger(__name__)

_UNSUPPORTED_QUERY_KEYS = frozenset(
    {"channel_binding", "sslmode", "sslcert", "sslkey", "sslrootcert", "sslcrl"}
)


def _clean_neon_url(url: str) -> str:
    """Drop query params that break asyncpg/psycopg2 (Neon adds channel_binding)."""
    parsed = urlparse(url)
    if not parsed.query:
        return url
    filtered = [(k, v) for k, v in parse_qsl(parsed.query) if k not in _UNSUPPORTED_QUERY_KEYS]
    query = urlencode(filtered)
    cleaned = urlunparse(parsed._replace(query=query))
    return cleaned.rstrip("?")


def _normalize_async_url(raw: str) -> str:
    url = _clean_neon_url(raw.strip())
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    return url


def _normalize_sync_url(raw: str) -> str:
    url = _clean_neon_url(raw.strip())
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def resolve_database_env() -> None:
    """Map POSTGRES_URL / Neon / Vercel Postgres vars to SQLAlchemy URLs."""

    def _get(name: str) -> str:
        return os.getenv(name, "").strip()

    async_url = _get("DATABASE_URL")
    sync_url = _get("DATABASE_URL_SYNC")
    if async_url and sync_url and "sqlite" in async_url and "sqlite" in sync_url:
        return

    raw = (
        _get("DATABASE_URL")
        or _get("POSTGRES_URL")
        or _get("STORAGE_URL")
        or _get("POSTGRES_PRISMA_URL")
        or _get("STORAGE_PRISMA_URL")
        or _get("POSTGRES_URL_NON_POOLING")
        or _get("STORAGE_URL_NON_POOLING")
        or _get("DATABASE_URL_UNPOOLED")
    )
    if not raw:
        return

    os.environ["DATABASE_URL"] = _normalize_async_url(raw)
    os.environ["DATABASE_URL_SYNC"] = _normalize_sync_url(raw)
    logger.info("Database URL resolved from environment (Postgres)")


def is_ephemeral_sqlite() -> bool:
    url = os.getenv("DATABASE_URL", "")
    return "sqlite" in url and "/tmp/" in url
