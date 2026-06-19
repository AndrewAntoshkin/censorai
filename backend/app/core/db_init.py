"""Lazy database initialization for Vercel serverless cold starts."""

import asyncio
import logging
import threading

from app.core.config import settings
from app.core.database import Base

logger = logging.getLogger(__name__)

_init_lock = threading.Lock()
_initialized = False
_init_error: str | None = None


def _ensure_unassigned_sync(sync_engine) -> None:
    from sqlalchemy.orm import Session

    from app.models.project import Project
    from app.services.project_buckets import UNASSIGNED_PROJECT_ID, UNASSIGNED_PROJECT_NAME

    with Session(sync_engine) as session:
        if session.get(Project, UNASSIGNED_PROJECT_ID) is None:
            session.add(
                Project(id=UNASSIGNED_PROJECT_ID, name=UNASSIGNED_PROJECT_NAME)
            )
            session.commit()
            logger.info("Created unassigned uploads project bucket")


def _migrate_columns() -> None:
    import sqlalchemy as sa

    sync_connect_args: dict = {}
    if "postgres" in settings.DATABASE_URL_SYNC:
        sync_connect_args = {"sslmode": "require"}

    sync_engine = sa.create_engine(
        settings.DATABASE_URL_SYNC,
        connect_args=sync_connect_args,
    )
    is_sqlite = "sqlite" in settings.DATABASE_URL_SYNC

    with sync_engine.begin() as conn:
        if is_sqlite:
            video_cols = {
                row[1] for row in conn.execute(sa.text("PRAGMA table_info(video_files)"))
            }
            if "replicate_prediction_id" not in video_cols:
                conn.execute(
                    sa.text(
                        "ALTER TABLE video_files ADD COLUMN replicate_prediction_id VARCHAR(128)"
                    )
                )
                logger.info("Added video_files.replicate_prediction_id column")

            scene_cols = {
                row[1] for row in conn.execute(sa.text("PRAGMA table_info(scenes)"))
            }
            if "mode" not in scene_cols:
                conn.execute(sa.text("ALTER TABLE scenes ADD COLUMN mode VARCHAR(50)"))
                logger.info("Added scenes.mode column")
            if "duration_seconds" not in video_cols:
                conn.execute(sa.text("ALTER TABLE video_files ADD COLUMN duration_seconds REAL"))
                logger.info("Added video_files.duration_seconds column")
            if "analysis_attempts" not in video_cols:
                conn.execute(
                    sa.text(
                        "ALTER TABLE video_files ADD COLUMN analysis_attempts "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                )
                logger.info("Added video_files.analysis_attempts column")
            if "report_kind" not in video_cols:
                conn.execute(
                    sa.text(
                        "ALTER TABLE video_files ADD COLUMN report_kind VARCHAR(32) "
                        "NOT NULL DEFAULT 'moderation'"
                    )
                )
                logger.info("Added video_files.report_kind column")
            if "placement_query" not in video_cols:
                conn.execute(sa.text("ALTER TABLE video_files ADD COLUMN placement_query VARCHAR(256)"))
                logger.info("Added video_files.placement_query column")

            project_cols = {
                row[1] for row in conn.execute(sa.text("PRAGMA table_info(projects)"))
            }
            if "owner_id" not in project_cols:
                conn.execute(
                    sa.text("ALTER TABLE projects ADD COLUMN owner_id VARCHAR(36)")
                )
                logger.info("Added projects.owner_id column")
            if "organization_id" not in project_cols:
                conn.execute(sa.text("ALTER TABLE projects ADD COLUMN organization_id VARCHAR(36)"))
                logger.info("Added projects.organization_id column")

            user_cols = {row[1] for row in conn.execute(sa.text("PRAGMA table_info(users)"))}
            if user_cols:
                if "organization_id" not in user_cols:
                    conn.execute(sa.text("ALTER TABLE users ADD COLUMN organization_id VARCHAR(36)"))
                if "role" not in user_cols:
                    conn.execute(
                        sa.text(
                            "ALTER TABLE users ADD COLUMN role VARCHAR(32) "
                            "NOT NULL DEFAULT 'member'"
                        )
                    )
            session_cols = {
                row[1] for row in conn.execute(sa.text("PRAGMA table_info(auth_sessions)"))
            }
            if session_cols and "active_organization_id" not in session_cols:
                conn.execute(
                    sa.text(
                        "ALTER TABLE auth_sessions ADD COLUMN active_organization_id VARCHAR(36)"
                    )
                )

            job_cols = {
                row[1] for row in conn.execute(sa.text("PRAGMA table_info(analysis_jobs)"))
            }
            if job_cols and "job_metadata" not in job_cols:
                conn.execute(sa.text("ALTER TABLE analysis_jobs ADD COLUMN job_metadata TEXT"))
                logger.info("Added analysis_jobs.job_metadata column")
        else:
            conn.execute(
                sa.text(
                    "ALTER TABLE video_files ADD COLUMN IF NOT EXISTS "
                    "replicate_prediction_id VARCHAR(128)"
                )
            )
            conn.execute(
                sa.text("ALTER TABLE scenes ADD COLUMN IF NOT EXISTS mode VARCHAR(50)")
            )
            conn.execute(
                sa.text(
                    "ALTER TABLE video_files ADD COLUMN IF NOT EXISTS "
                    "duration_seconds DOUBLE PRECISION"
                )
            )
            conn.execute(
                sa.text(
                    "ALTER TABLE video_files ADD COLUMN IF NOT EXISTS "
                    "analysis_attempts INTEGER NOT NULL DEFAULT 0"
                )
            )
            conn.execute(
                sa.text(
                    "ALTER TABLE upload_chunk_sessions ADD COLUMN IF NOT EXISTS "
                    "duration_seconds DOUBLE PRECISION"
                )
            )
            conn.execute(
                sa.text(
                    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS owner_id VARCHAR(36) "
                    "REFERENCES users(id) ON DELETE SET NULL"
                )
            )
            conn.execute(
                sa.text(
                    "ALTER TABLE projects ADD COLUMN IF NOT EXISTS "
                    "organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE CASCADE"
                )
            )
            conn.execute(
                sa.text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                    "organization_id VARCHAR(36) REFERENCES organizations(id) ON DELETE RESTRICT"
                )
            )
            conn.execute(
                sa.text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(32) "
                    "NOT NULL DEFAULT 'member'"
                )
            )
            conn.execute(
                sa.text(
                    "ALTER TABLE auth_sessions ADD COLUMN IF NOT EXISTS "
                    "active_organization_id VARCHAR(36) "
                    "REFERENCES organizations(id) ON DELETE SET NULL"
                )
            )
            conn.execute(
                sa.text(
                    "ALTER TABLE analysis_jobs ADD COLUMN IF NOT EXISTS job_metadata TEXT"
                )
            )
            conn.execute(
                sa.text(
                    "ALTER TABLE video_files ADD COLUMN IF NOT EXISTS "
                    "report_kind VARCHAR(32) NOT NULL DEFAULT 'moderation'"
                )
            )
            conn.execute(
                sa.text(
                    "ALTER TABLE video_files ADD COLUMN IF NOT EXISTS "
                    "placement_query VARCHAR(256)"
                )
            )
            logger.info(
                "Ensured video_files, scenes, projects, users, auth_sessions, "
                "analysis_jobs columns"
            )


def _ensure_organizations_sync(sync_engine) -> None:
    from sqlalchemy import select, update
    from sqlalchemy.orm import Session

    from app.models.organization import Organization, RegistrationCode
    from app.models.project import Project
    from app.services.organization_service import (
        FRAMECHECK_SLUG,
        normalize_registration_code,
    )
    from app.services.project_buckets import UNASSIGNED_PROJECT_ID

    with Session(sync_engine) as session:
        org = session.scalar(
            select(Organization).where(Organization.slug == FRAMECHECK_SLUG)
        )
        if org is None:
            org = Organization(name=settings.FRAMECHECK_ORG_NAME, slug=FRAMECHECK_SLUG)
            session.add(org)
            session.flush()

        code_value = normalize_registration_code(settings.FRAMECHECK_REGISTRATION_CODE)
        existing_code = session.scalar(
            select(RegistrationCode).where(RegistrationCode.code == code_value)
        )
        if existing_code is None:
            session.add(
                RegistrationCode(
                    code=code_value,
                    organization_id=org.id,
                    label="Framecheck default",
                )
            )
        elif existing_code.organization_id != org.id:
            logger.warning(
                "Registration code %s belongs to another org; skipping reassign",
                code_value,
            )

        session.execute(
            update(Project)
            .where(
                Project.id != UNASSIGNED_PROJECT_ID,
                Project.organization_id.is_(None),
            )
            .values(organization_id=org.id)
        )
        session.commit()
        logger.info(
            "Organizations ready (slug=%s, invite code=%s)",
            FRAMECHECK_SLUG,
            code_value,
        )


def _init_sync() -> None:
    global _initialized, _init_error

    with _init_lock:
        if _initialized:
            return
        if _init_error:
            raise RuntimeError(_init_error)

        try:
            import app.models  # noqa: F401
            import sqlalchemy as sa

            sync_connect_args: dict = {}
            if "sqlite" in settings.DATABASE_URL_SYNC:
                sync_connect_args = {"check_same_thread": False}

            sync_engine = sa.create_engine(
                settings.DATABASE_URL_SYNC,
                connect_args=sync_connect_args,
            )
            Base.metadata.create_all(sync_engine)
            _migrate_columns()
            _ensure_unassigned_sync(sync_engine)
            _ensure_organizations_sync(sync_engine)

            sync_engine.dispose()

            from app.services.seed_bundle import ensure_demo_seeded

            try:
                ensure_demo_seeded()
            except Exception:
                # Demo content is optional for API availability; do not block all
                # endpoints if bundle import hits a duplicate/legacy row conflict.
                logger.exception("Demo seed failed; continuing without reseed")
            _initialized = True
            db_kind = "postgres" if "postgres" in settings.DATABASE_URL else "sqlite"
            logger.info("Database initialized (%s)", db_kind)
        except Exception as exc:
            _init_error = str(exc)
            logger.exception("Database initialization failed")
            raise


async def ensure_database() -> None:
    await asyncio.to_thread(_init_sync)


def database_status() -> dict:
    return {
        "initialized": _initialized,
        "error": _init_error,
        "url_scheme": settings.DATABASE_URL.split("://", 1)[0],
    }
