"""Seed demo project from bundled JSON (used on Vercel cold start)."""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.analysis import Analysis, Scene
from app.models.project import Project, VideoFile

logger = logging.getLogger(__name__)

BUNDLE_PATH = Path(__file__).resolve().parents[2] / "demo" / "bundle.json"
DEMO_MARKER = "Демо — видеоконтент"

_seed_lock = threading.Lock()
_demo_ready = False


def _demo_exists() -> bool:
    engine = create_engine(settings.DATABASE_URL_SYNC)
    with Session(engine) as session:
        return bool(
            session.scalar(select(Project.id).where(Project.name == DEMO_MARKER))
        )


def ensure_demo_seeded() -> bool:
    """Load demo bundle once per process if the demo project is missing."""
    global _demo_ready

    with _seed_lock:
        if _demo_ready:
            return False

        if _demo_exists():
            _demo_ready = True
            return False

        seeded = load_demo_bundle_if_empty()
        if seeded or _demo_exists():
            _demo_ready = True
        return seeded


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_demo_bundle_if_empty() -> bool:
    if not BUNDLE_PATH.exists():
        logger.warning("Demo bundle not found at %s", BUNDLE_PATH)
        return False

    engine = create_engine(settings.DATABASE_URL_SYNC)
    with Session(engine) as session:
        demo_exists = session.scalar(
            select(Project.id).where(Project.name == DEMO_MARKER)
        )
        if demo_exists:
            return False

        bundle = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
        project_data = bundle["project"]

        project = Project(
            id=project_data["id"],
            name=project_data["name"],
            created_at=_parse_dt(project_data.get("created_at")) or datetime.utcnow(),
        )
        session.add(project)
        session.flush()

        analyses_map: dict[str, dict] = bundle.get("analyses", {})
        files = project_data.get("files") or bundle.get("recent") or []

        for file_data in files:
            analysis_payload = analyses_map.get(file_data["id"])
            analysis_id = None

            if analysis_payload:
                analysis = Analysis(
                    id=analysis_payload["id"],
                    video_file_id=file_data["id"],
                    video_title=analysis_payload.get("video_title"),
                    duration=analysis_payload.get("duration"),
                    analyzed_at=_parse_dt(analysis_payload.get("analyzed_at")),
                    status=analysis_payload.get("status", "completed"),
                    created_at=_parse_dt(analysis_payload.get("created_at")) or datetime.utcnow(),
                )
                analysis.summary = analysis_payload.get("summary")
                session.add(analysis)
                session.flush()
                analysis_id = analysis.id

                for scene_data in analysis_payload.get("scenes", []):
                    session.add(
                        Scene(
                            id=scene_data["id"],
                            analysis_id=analysis.id,
                            scene_number=scene_data["scene_number"],
                            start_time=scene_data.get("start_time"),
                            end_time=scene_data.get("end_time"),
                            description=scene_data.get("description"),
                            risk=scene_data.get("risk"),
                            risk_level=scene_data.get("risk_level"),
                            probability=scene_data.get("probability"),
                            reason=scene_data.get("reason"),
                            quote=scene_data.get("quote"),
                            text_in_frame=scene_data.get("text_in_frame"),
                            recommendation=scene_data.get("recommendation"),
                        )
                    )

            session.add(
                VideoFile(
                    id=file_data["id"],
                    name=file_data["name"],
                    size=file_data.get("size", 0),
                    status=file_data.get("status", "analyzed"),
                    progress=file_data.get("progress", 100),
                    project_id=project.id,
                    folder_id=file_data.get("folder_id"),
                    storage_path=file_data.get("storage_path"),
                    analysis_id=analysis_id,
                    created_at=_parse_dt(file_data.get("created_at")) or datetime.utcnow(),
                )
            )

        session.commit()
        logger.info("Seeded demo project with %d files", len(files))
        return True
