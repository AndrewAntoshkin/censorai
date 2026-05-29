import json
import logging
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.models.analysis import Analysis, Scene
from app.models.project import Project, VideoFile
from app.schemas.analysis import AnalysisResponse
from app.services.docx_service import generate_report
from app.services.storage_service import storage_service
from app.services.text_analysis_service import text_analysis_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/books", tags=["books"])

ALLOWED_EXTENSIONS = {".pdf"}


@router.post("/upload", status_code=201)
async def upload_book(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.UPLOAD_MAX_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f}MB (max {settings.UPLOAD_MAX_SIZE_MB}MB)",
        )

    project_id = await _ensure_books_project(db)
    storage_path = await storage_service.save_upload(project_id, file.filename, content)

    book = VideoFile(
        name=file.filename,
        size=len(content),
        status="uploaded",
        progress=100,
        project_id=project_id,
        storage_path=storage_path,
    )
    db.add(book)
    await db.flush()
    await db.refresh(book)

    return {
        "id": book.id,
        "name": book.name,
        "size": book.size,
        "status": book.status,
    }


@router.post("/{book_id}/analyze", response_model=AnalysisResponse)
async def analyze_book(book_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VideoFile).where(VideoFile.id == book_id)
    )
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if not book.storage_path:
        raise HTTPException(status_code=400, detail="Book has no storage path")

    book.status = "analyzing"
    book.progress = 0
    await db.flush()
    await db.commit()

    try:
        gemini_result = await text_analysis_service.analyze_text(book.storage_path)
    except Exception as e:
        logger.exception("Text analysis failed for book %s", book_id)
        book.status = "error"
        await db.flush()
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}") from e

    summary = _build_summary_dict(gemini_result)
    analysis = Analysis(
        video_file_id=book_id,
        video_title=gemini_result.video_title or book.name,
        duration=gemini_result.duration,
        analyzed_at=datetime.now(timezone.utc),
        status="completed",
    )
    analysis.summary = summary
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)

    for gs in gemini_result.scenes:
        if gs.risks:
            for risk_item in gs.risks:
                scene = Scene(
                    analysis_id=analysis.id,
                    scene_number=gs.scene_number,
                    start_time=gs.start_time,
                    end_time=gs.end_time,
                    description=gs.description,
                    risk=risk_item.risk,
                    risk_level=risk_item.risk_level,
                    probability=risk_item.probability,
                    reason=risk_item.reason,
                    quote=risk_item.quote,
                    text_in_frame=risk_item.text_in_frame,
                    recommendation=risk_item.recommendation,
                )
                db.add(scene)
        else:
            scene = Scene(
                analysis_id=analysis.id,
                scene_number=gs.scene_number,
                start_time=gs.start_time,
                end_time=gs.end_time,
                description=gs.description,
            )
            db.add(scene)

    book.status = "analyzed"
    book.progress = 100
    book.analysis_id = analysis.id
    await db.flush()
    await db.commit()

    analysis_result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.scenes))
        .where(Analysis.id == analysis.id)
    )
    return analysis_result.scalar_one()


@router.get("/{book_id}/analysis", response_model=AnalysisResponse)
async def get_book_analysis(book_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VideoFile).where(VideoFile.id == book_id)
    )
    book = result.scalar_one_or_none()
    if not book or not book.analysis_id:
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis_result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.scenes))
        .where(Analysis.id == book.analysis_id)
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.get("/{book_id}/report")
async def download_book_report(book_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VideoFile).where(VideoFile.id == book_id)
    )
    book = result.scalar_one_or_none()
    if not book or not book.analysis_id:
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis_result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.scenes))
        .where(Analysis.id == book.analysis_id)
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis_response = AnalysisResponse.model_validate(analysis)
    docx_bytes = generate_report(analysis_response)

    filename = f"censor_report_{book.name}.docx"
    encoded = quote(filename)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
        },
    )


BOOKS_PROJECT_ID = "books-project"


async def _ensure_books_project(db: AsyncSession) -> str:
    result = await db.execute(
        select(Project).where(Project.id == BOOKS_PROJECT_ID)
    )
    if not result.scalar_one_or_none():
        project = Project(id=BOOKS_PROJECT_ID, name="Книги")
        db.add(project)
        await db.flush()
    return BOOKS_PROJECT_ID


def _build_summary_dict(gemini_result) -> dict:
    total = len(gemini_result.scenes)
    risky = 0
    categories: dict[str, int] = {}
    critical = 0
    warning = 0

    for gs in gemini_result.scenes:
        if gs.risks:
            risky += 1
            for r in gs.risks:
                if r.risk:
                    categories[r.risk] = categories.get(r.risk, 0) + 1
                if r.risk_level == "critical":
                    critical += 1
                elif r.risk_level == "warning":
                    warning += 1

    return {
        "total_scenes": total,
        "risky_scenes": risky,
        "risk_categories": categories,
        "critical_count": critical,
        "warning_count": warning,
    }
