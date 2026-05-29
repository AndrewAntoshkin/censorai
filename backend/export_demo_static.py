"""Экспорт демо-данных в JSON для статического фронтенда (GitHub Pages).

Запуск: python export_demo_static.py
"""

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models.analysis import Analysis
from app.models.project import Project, VideoFile

DEMO_PROJECT_NAME = "Демо — видеоконтент"
OUT_DIR = Path(__file__).resolve().parent.parent / "frontend" / "public" / "demo"


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _file_payload(vf: VideoFile) -> dict:
    analysis_brief = None
    if vf.analysis:
        analysis_brief = {
            "id": vf.analysis.id,
            "status": vf.analysis.status,
            "summary": vf.analysis.summary,
            "analyzed_at": _iso(vf.analysis.analyzed_at),
        }
    return {
        "id": vf.id,
        "name": vf.name,
        "size": vf.size,
        "status": vf.status,
        "progress": vf.progress,
        "project_id": vf.project_id,
        "folder_id": vf.folder_id,
        "storage_path": vf.storage_path,
        "analysis_id": vf.analysis_id,
        "analysis": analysis_brief,
        "created_at": _iso(vf.created_at),
    }


def _analysis_payload(analysis: Analysis) -> dict:
    return {
        "id": analysis.id,
        "video_file_id": analysis.video_file_id,
        "video_title": analysis.video_title,
        "duration": analysis.duration,
        "analyzed_at": _iso(analysis.analyzed_at),
        "summary": analysis.summary,
        "status": analysis.status,
        "created_at": _iso(analysis.created_at),
        "scenes": [
            {
                "id": sc.id,
                "analysis_id": sc.analysis_id,
                "scene_number": sc.scene_number,
                "start_time": sc.start_time,
                "end_time": sc.end_time,
                "description": sc.description,
                "risk": sc.risk,
                "risk_level": sc.risk_level,
                "probability": sc.probability,
                "reason": sc.reason,
                "quote": sc.quote,
                "text_in_frame": sc.text_in_frame,
                "recommendation": sc.recommendation,
            }
            for sc in sorted(analysis.scenes, key=lambda s: s.scene_number)
        ],
    }


def main() -> None:
    engine = create_engine(settings.DATABASE_URL_SYNC)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with Session(engine) as session:
        demo = session.scalar(select(Project).where(Project.name == DEMO_PROJECT_NAME))
        if demo is None:
            raise SystemExit(f"Проект «{DEMO_PROJECT_NAME}» не найден. Сначала запустите seed_demo.py")

        files = session.scalars(
            select(VideoFile)
            .options(selectinload(VideoFile.analysis))
            .where(VideoFile.project_id == demo.id)
            .order_by(VideoFile.name)
        ).all()

        analyses: dict[str, dict] = {}
        file_payloads = []
        for vf in files:
            file_payloads.append(_file_payload(vf))
            if not vf.analysis_id:
                continue
            analysis = session.scalar(
                select(Analysis)
                .options(selectinload(Analysis.scenes))
                .where(Analysis.id == vf.analysis_id)
            )
            if analysis:
                analyses[vf.id] = _analysis_payload(analysis)

        project_payload = {
            "id": demo.id,
            "name": demo.name,
            "created_at": _iso(demo.created_at),
            "files_count": len(file_payloads),
            "folders": [],
            "files": file_payloads,
        }

        bundle = {
            "project": project_payload,
            "projects": [project_payload],
            "recent": file_payloads,
            "analyses": analyses,
            "fileIds": [f["id"] for f in file_payloads],
            "projectIds": [demo.id],
        }

    (OUT_DIR / "bundle.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    routes = {
        "fileIds": bundle["fileIds"],
        "projectIds": bundle["projectIds"],
    }
    (OUT_DIR / "routes.json").write_text(
        json.dumps(routes, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Экспортировано: {len(file_payloads)} файлов, {len(analyses)} анализов")
    print(f"→ {OUT_DIR / 'bundle.json'}")


if __name__ == "__main__":
    main()
