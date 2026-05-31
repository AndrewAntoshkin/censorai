import asyncio
import logging
import mimetypes
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.models.analysis import Analysis, Scene
from app.models.project import VideoFile
from app.schemas.analysis import AnalysisResponse, GeminiAnalysisResult
from app.schemas.project import (
    BlobUploadRequest,
    ChunkUploadInitRequest,
    ChunkUploadInitResponse,
    ChunkUploadStatusResponse,
    VideoFileResponse,
)
from app.services.chunk_upload_service import (
    chunk_size_bytes,
    cleanup_session,
    create_session,
    merge_session,
    save_part,
)
from app.services.docx_service import generate_report
from app.services.gemini_service import gemini_service
from app.services.replicate_media import verify_replicate_media_signature
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.route_prefix("/files"), tags=["files"])


async def _kickoff_analysis(video: VideoFile, db: AsyncSession) -> None:
    """Start Replicate job. Must run on the same instance that holds the file (Vercel /tmp)."""
    if not video.storage_path:
        raise HTTPException(status_code=400, detail="File has no storage path")

    path = Path(video.storage_path)
    if not video.storage_path.startswith(("http://", "https://")) and not path.exists():
        raise HTTPException(
            status_code=503,
            detail="Video file not found on server. Retry upload on Vercel or use persistent storage.",
        )

    video.status = "analyzing"
    video.progress = 10
    await db.flush()

    try:
        prediction_id = await asyncio.to_thread(
            gemini_service.start_analysis,
            video.storage_path,
            file_id=video.id,
            file_size=video.size,
        )
    except Exception as exc:
        logger.exception("Failed to start analysis for file %s", video.id)
        video.status = "error"
        video.replicate_prediction_id = None
        await db.flush()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    video.replicate_prediction_id = prediction_id
    video.progress = 30
    await db.flush()


async def _maybe_finish_analysis(video: VideoFile, db: AsyncSession) -> None:
    if video.status != "analyzing" or not video.replicate_prediction_id:
        return

    try:
        _status, result = await asyncio.to_thread(
            gemini_service.poll_prediction, video.replicate_prediction_id
        )
    except Exception as exc:
        err = str(exc).lower()
        if (
            ("interrupted" in err or "code: pa" in err)
            and video.storage_path
            and video.progress < 90
        ):
            path_ok = video.storage_path.startswith(("http://", "https://")) or Path(
                video.storage_path
            ).exists()
            if not path_ok:
                logger.error(
                    "Replicate PA but video file missing on this instance for %s",
                    video.id,
                )
            else:
                logger.warning("Replicate interrupted, retrying analysis for file %s", video.id)
                try:
                    prediction_id = await asyncio.to_thread(
                        gemini_service.start_analysis,
                        video.storage_path,
                        file_id=video.id,
                        file_size=video.size,
                    )
                    video.replicate_prediction_id = prediction_id
                    video.progress = min(video.progress + 10, 85)
                    await db.flush()
                    return
                except Exception:
                    logger.exception("Retry failed for file %s", video.id)

        logger.exception("Poll failed for file %s", video.id)
        video.status = "error"
        video.replicate_prediction_id = None
        await db.flush()
        return

    if result is None:
        video.progress = min(95, video.progress + 5)
        await db.flush()
        return

    try:
        await _save_analysis_result(video, db, result)
        video.replicate_prediction_id = None
    except Exception:
        logger.exception("Failed to save analysis for file %s", video.id)
        video.status = "error"
        video.replicate_prediction_id = None
        await db.flush()


async def _save_analysis_result(
    video: VideoFile, db: AsyncSession, gemini_result: GeminiAnalysisResult
) -> Analysis:
    summary = _build_summary_dict(gemini_result)
    analysis = Analysis(
        video_file_id=video.id,
        video_title=gemini_result.video_title or video.name,
        duration=gemini_result.duration,
        analyzed_at=datetime.now(timezone.utc),
        status="completed",
    )
    analysis.summary = summary
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)

    for gs in gemini_result.scenes:
        if not gs.risks:
            continue
        for risk_item in gs.risks:
            scene = Scene(
                analysis_id=analysis.id,
                scene_number=gs.scene_number,
                start_time=gs.start_time,
                end_time=gs.end_time,
                description=gs.description,
                risk=risk_item.risk,
                mode=risk_item.mode,
                risk_level=risk_item.risk_level,
                probability=risk_item.probability,
                reason=risk_item.reason,
                quote=risk_item.quote,
                text_in_frame=risk_item.text_in_frame,
                recommendation=risk_item.recommendation,
            )
            db.add(scene)

    video.status = "analyzed"
    video.progress = 100
    video.analysis_id = analysis.id
    await db.flush()
    return analysis


@router.post("/upload", response_model=VideoFileResponse, status_code=201)
async def upload_file(
    project_id: str,
    file: UploadFile,
    folder_id: str | None = None,
    auto_analyze: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.UPLOAD_MAX_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f}MB (max {settings.UPLOAD_MAX_SIZE_MB}MB)",
        )

    storage_path = await storage_service.save_upload(project_id, file.filename, content)

    video = VideoFile(
        name=file.filename,
        size=len(content),
        status="uploaded",
        progress=100,
        project_id=project_id,
        folder_id=folder_id,
        storage_path=storage_path,
    )
    db.add(video)
    await db.flush()
    await db.refresh(video)

    if auto_analyze:
        await _kickoff_analysis(video, db)
        await db.refresh(video)

    return video


@router.post("/upload-chunks/init", response_model=ChunkUploadInitResponse, status_code=201)
async def init_chunk_upload(data: ChunkUploadInitRequest):
    try:
        session = create_session(
            filename=data.filename,
            size=data.size,
            project_id=data.project_id,
            folder_id=data.folder_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e)) from e

    return ChunkUploadInitResponse(
        session_id=session.session_id,
        chunk_size=chunk_size_bytes(),
        total_parts=session.total_parts,
    )


@router.put("/upload-chunks/{session_id}/parts/{part}")
async def upload_chunk(session_id: str, part: int, request: Request):
    content = await request.body()
    if not content:
        raise HTTPException(status_code=400, detail="Empty chunk body")

    try:
        session = save_part(session_id, part, content)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return ChunkUploadStatusResponse(
        session_id=session.session_id,
        received_parts=sorted(session.received_parts),
        total_parts=session.total_parts,
        complete=len(session.received_parts) == session.total_parts,
    )


@router.post("/upload-chunks/{session_id}/complete", response_model=VideoFileResponse, status_code=201)
async def complete_chunk_upload(
    session_id: str,
    auto_analyze: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    try:
        merged_path, session = merge_session(session_id)
        storage_path = await storage_service.save_upload_from_path(
            session.project_id, session.filename, merged_path
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    cleanup_session(session_id)

    video = VideoFile(
        name=session.filename,
        size=session.size,
        status="uploaded",
        progress=100,
        project_id=session.project_id,
        folder_id=session.folder_id,
        storage_path=storage_path,
    )
    db.add(video)
    await db.flush()
    await db.refresh(video)

    if auto_analyze:
        await _kickoff_analysis(video, db)
        await db.refresh(video)

    return video


@router.post("/from-blob", response_model=VideoFileResponse, status_code=201)
async def register_from_blob(
    project_id: str,
    data: BlobUploadRequest,
    folder_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    size_mb = data.size / (1024 * 1024)
    if size_mb > settings.UPLOAD_MAX_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f}MB (max {settings.UPLOAD_MAX_SIZE_MB}MB)",
        )

    video = VideoFile(
        name=data.filename,
        size=data.size,
        status="uploaded",
        progress=100,
        project_id=project_id,
        folder_id=folder_id,
        storage_path=data.blob_url,
    )
    db.add(video)
    await db.flush()
    await db.refresh(video)
    return video


@router.get("/recent", response_model=list[VideoFileResponse])
async def recent_files(
    limit: int = 12,
    analyzed_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    import asyncio

    from app.services.seed_bundle import ensure_demo_seeded

    await asyncio.to_thread(ensure_demo_seeded)

    stmt = (
        select(VideoFile)
        .options(selectinload(VideoFile.analysis))
        .order_by(VideoFile.created_at.desc())
        .limit(max(1, min(limit, 100)))
    )
    if analyzed_only:
        stmt = stmt.where(VideoFile.analysis_id.is_not(None))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{file_id}", response_model=VideoFileResponse)
async def get_file(file_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VideoFile)
        .options(selectinload(VideoFile.analysis))
        .where(VideoFile.id == file_id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="File not found")

    await _maybe_finish_analysis(video, db)
    await db.refresh(video)
    return video


@router.get("/{file_id}/analysis", response_model=AnalysisResponse)
async def get_analysis(file_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VideoFile).where(VideoFile.id == file_id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="File not found")

    await _maybe_finish_analysis(video, db)
    await db.refresh(video)

    if not video.analysis_id:
        if video.status == "analyzing":
            raise HTTPException(status_code=202, detail="Analysis in progress")
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis_result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.scenes))
        .where(Analysis.id == video.analysis_id)
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.post("/{file_id}/analyze")
async def analyze_file(file_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VideoFile).where(VideoFile.id == file_id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="File not found")

    if not video.storage_path:
        raise HTTPException(status_code=400, detail="File has no storage path")

    if video.status == "analyzed" and video.analysis_id:
        analysis_result = await db.execute(
            select(Analysis)
            .options(selectinload(Analysis.scenes))
            .where(Analysis.id == video.analysis_id)
        )
        return analysis_result.scalar_one()

    if video.status == "analyzing" and video.replicate_prediction_id:
        return JSONResponse(
            status_code=202,
            content={"status": "analyzing", "file_id": file_id},
        )

    video.status = "analyzing"
    video.progress = 10
    await db.flush()

    try:
        await _kickoff_analysis(video, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to start analysis for file %s", file_id)
        video.status = "error"
        await db.flush()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}") from e

    await db.commit()

    return JSONResponse(
        status_code=202,
        content={"status": "analyzing", "file_id": file_id},
    )


@router.get("/{file_id}/replicate-media")
async def replicate_media(
    file_id: str,
    expires: int = Query(...),
    sig: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Temporary signed URL for Replicate to fetch large videos (no session auth)."""
    if not verify_replicate_media_signature(file_id, expires, sig):
        raise HTTPException(status_code=403, detail="Invalid or expired signature")

    result = await db.execute(select(VideoFile).where(VideoFile.id == file_id))
    video = result.scalar_one_or_none()
    if not video or not video.storage_path:
        raise HTTPException(status_code=404, detail="File not found")

    if video.storage_path.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Remote storage path cannot be streamed")

    path = Path(video.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    media_type = mimetypes.guess_type(path.name)[0] or "video/mp4"
    return FileResponse(
        path,
        media_type=media_type,
        filename=video.name,
    )


@router.get("/{file_id}/report")
async def download_report(file_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(VideoFile).where(VideoFile.id == file_id)
    )
    video = result.scalar_one_or_none()
    if not video or not video.analysis_id:
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis_result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.scenes))
        .where(Analysis.id == video.analysis_id)
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis_response = AnalysisResponse.model_validate(analysis)
    docx_bytes = generate_report(analysis_response)

    from urllib.parse import quote
    filename = f"censor_report_{video.name}.docx"
    encoded = quote(filename)
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded}",
        },
    )


def _build_summary_dict(gemini_result) -> dict:
    scenes_with_risks = [gs for gs in gemini_result.scenes if gs.risks]
    total_reviewed = gemini_result.total_scenes_reviewed or len(gemini_result.scenes)
    risky_scene_numbers = {gs.scene_number for gs in scenes_with_risks}
    categories: dict[str, int] = {}
    critical = 0
    warning = 0

    for gs in scenes_with_risks:
        for r in gs.risks:
            if r.risk:
                categories[r.risk] = categories.get(r.risk, 0) + 1
            if r.risk_level == "critical":
                critical += 1
            elif r.risk_level == "warning":
                warning += 1

    summary: dict = {
        "total_scenes": total_reviewed,
        "risky_scenes": len(risky_scene_numbers),
        "risk_categories": categories,
        "critical_count": critical,
        "warning_count": warning,
    }

    if gemini_result.recommended_age_rating:
        summary["recommended_age_rating"] = gemini_result.recommended_age_rating
    if gemini_result.age_rating_reason:
        summary["age_rating_reason"] = gemini_result.age_rating_reason
    if gemini_result.age_rating_triggers:
        summary["age_rating_triggers"] = [
            t.model_dump(exclude_none=True) for t in gemini_result.age_rating_triggers
        ]
    if gemini_result.entities:
        summary["entities"] = [e.model_dump(exclude_none=True) for e in gemini_result.entities]
    if gemini_result.markings_detected:
        summary["markings_detected"] = [
            m.model_dump(exclude_none=True) for m in gemini_result.markings_detected
        ]

    return summary
