import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.books import router as books_router
from app.api.files import router as files_router
from app.api.ops import router as ops_router
from app.api.projects import router as projects_router
from app.core.config import settings
from app.core.database import engine
from app.core.db_init import database_status, ensure_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("App starting (database init deferred)")
    yield
    await engine.dispose()


app = FastAPI(
    title="фреймчек",
    description="Сервис анализа видеоконтента на соответствие требованиям",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(files_router)
app.include_router(books_router)
app.include_router(ops_router)


@app.get(settings.route_prefix("/worker/poll-once"))
async def worker_poll_once(secret: str | None = Query(None)):
    """Manual poll tick for local dev. Requires WORKER_DEV_POLL_SECRET or non-Vercel host."""
    from app.services.analysis_orchestration import run_analysis_poll_cycle

    expected = settings.WORKER_DEV_POLL_SECRET.strip()
    if expected:
        if secret != expected:
            raise HTTPException(status_code=403, detail="Invalid worker poll secret")
    elif os.getenv("VERCEL"):
        raise HTTPException(status_code=404, detail="Not available")

    return await run_analysis_poll_cycle()


@app.get(settings.route_prefix("/health"))
async def health_check():
    import os

    from app.core.db_url import is_ephemeral_sqlite

    db = "postgres" if "postgres" in settings.DATABASE_URL else "sqlite"
    payload = {
        "status": "ok",
        "service": "framecheck",
        "database": db,
        "ephemeral_db": is_ephemeral_sqlite(),
        "env": {
            "has_database_url": bool(os.getenv("DATABASE_URL", "").strip()),
            "has_postgres_url": bool(os.getenv("POSTGRES_URL", "").strip()),
            "has_storage_url": bool(os.getenv("STORAGE_URL", "").strip()),
            "replicate_max_output_tokens": settings.REPLICATE_MAX_OUTPUT_TOKENS,
            "analysis_max_coverage_retries": settings.ANALYSIS_MAX_COVERAGE_RETRIES,
            "auth_required": settings.AUTH_REQUIRED,
        },
        "db": database_status(),
    }
    try:
        await ensure_database()
        payload["db"] = database_status()
        payload["status"] = "ok"
    except Exception as exc:
        payload["status"] = "degraded"
        payload["db_error"] = str(exc)
    return payload


@app.get(settings.route_prefix("/legal/registries"))
async def legal_registries_status():
    from app.services.legal_registry import registry_status

    return registry_status()


@app.post(settings.route_prefix("/seed-demo"))
async def seed_demo():
    import asyncio

    from app.services.seed_bundle import ensure_demo_seeded

    seeded = await asyncio.to_thread(ensure_demo_seeded)
    return {"seeded": seeded}
