import asyncio
import json
import logging
import mimetypes
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import CurrentAuth, require_auth_if_enabled
from app.core.filename import normalize_filename
from app.models.analysis import Analysis, Scene
from app.models.project import Project, VideoFile
from app.services.access import apply_files_scope, require_project_access
from app.schemas.analysis import AnalysisResponse, GeminiAnalysisResult
from app.schemas.project import (
    AssignProjectRequest,
    BlobUploadRequest,
    ChunkUploadInitRequest,
    ChunkUploadInitResponse,
    ChunkUploadStatusResponse,
    PresignUploadRequest,
    PresignUploadResponse,
    UploadStrategyResponse,
    VideoFileResponse,
)
from app.services.project_buckets import is_system_project, resolve_project_id
from app.services.chunk_upload_service import (
    chunk_size_bytes,
    cleanup_session,
    create_session,
    merge_session,
    save_part,
)
from app.services.docx_service import generate_report
from app.services.analysis_coverage import (
    expected_duration_seconds,
    is_incomplete_coverage,
)
from app.services.analysis_finish import maybe_finish_analysis
from app.services.gemini_service import gemini_service
from app.services.replicate_media import verify_replicate_media_signature
from app.services.object_storage import build_object_key
from app.services.storage_service import storage_service
from app.services.legal_compliance import enrich_analysis_summary
from app.services.video_blob_cleanup import release_video_blob
from app.services.video_media import ensure_public_video_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.route_prefix("/files"), tags=["files"])


async def _load_project(db: AsyncSession, project_id: str) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _ensure_project_access(
    db: AsyncSession,
    auth: CurrentAuth | None,
    project_id: str,
) -> Project:
    project = await _load_project(db, project_id)
    user = auth.user if auth else None
    session = auth.session if auth else None
    require_project_access(user, project, session)
    return project


async def _ensure_video_access(
    db: AsyncSession, auth: CurrentAuth | None, file_id: str
) -> VideoFile:
    result = await db.execute(select(VideoFile).where(VideoFile.id == file_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="File not found")
    await _ensure_project_access(db, auth, video.project_id)
    return video


def _expected_duration(video: VideoFile) -> int | None:
    return expected_duration_seconds(video.size or 0, video.duration_seconds)


async def _cascade_prompt_suffix(video: VideoFile) -> str:
    if not settings.ANALYSIS_CASCADE_ENABLED:
        return ""
    from app.services.cascade_media import cleanup_temp_path, resolve_local_video_path
    from app.services.scene_detection import detect_scene_timestamps, scene_hints_for_prompt

    local_path, temp_file = await asyncio.to_thread(
        resolve_local_video_path, video.storage_path or ""
    )
    if not local_path:
        return ""
    try:
        timestamps = await asyncio.to_thread(detect_scene_timestamps, local_path)
        return scene_hints_for_prompt(timestamps)
    finally:
        if temp_file is not None:
            await asyncio.to_thread(cleanup_temp_path, temp_file)


async def _restart_full_analysis(video: VideoFile, db: AsyncSession) -> None:
    """Start a new run when the previous output did not cover the full file."""
    if not video.storage_path:
        return
    video.status = "analyzing"
    video.progress = max(25, video.progress or 0)
    video.analysis_id = None
    video.replicate_prediction_id = None
    await db.flush()
    await _kickoff_analysis(video, db, from_queue=True)


async def _kickoff_analysis(
    video: VideoFile, db: AsyncSession, *, from_queue: bool = False
) -> None:
    """Queue job, then start non-blocking Replicate prediction."""
    from app.services.analysis_jobs import (
        ensure_processing_job,
        ensure_queued_job,
        mark_job_failed,
    )
    from app.services.video_analysis_provider import start_analysis

    if not settings.REPLICATE_API_TOKEN.strip():
        raise HTTPException(
            status_code=503,
            detail=(
                "REPLICATE_API_TOKEN не задан локально. "
                "Скопируйте из Vercel (Production) в backend/.env.secrets "
                "или запустите: ./scripts/import-secrets.sh"
            ),
        )

    if not video.storage_path:
        raise HTTPException(status_code=400, detail="File has no storage path")

    path = Path(video.storage_path)
    if (
        not video.storage_path.startswith(("http://", "https://", "s3://"))
        and not path.exists()
    ):
        raise HTTPException(
            status_code=503,
            detail="Video file not found on server. Use Blob or S3 upload.",
        )

    if not from_queue:
        await ensure_queued_job(db, video.id)

    video.status = "analyzing"
    video.progress = 20 if not from_queue else max(video.progress or 0, 20)
    if not from_queue:
        video.analysis_attempts = 0
    await db.flush()

    from app.services.segmented_analysis import (
        prepare_segmented_job,
        should_segment,
        start_segment_prediction,
    )

    do_segment, total_seconds = await should_segment(video)
    if total_seconds and (not video.duration_seconds or video.duration_seconds < 30):
        video.duration_seconds = float(total_seconds)
        await db.flush()
    extra_prompt = await _cascade_prompt_suffix(video) if not do_segment else ""

    try:
        if do_segment and total_seconds:
            metadata = await prepare_segmented_job(
                video,
                db,
                total_seconds=total_seconds,
                extra_prompt_suffix=extra_prompt,
            )
            prediction_id = await start_segment_prediction(video, db, metadata, 0)
            video.progress = 28
        else:
            await ensure_public_video_url(video, db)
            prediction_id = await asyncio.to_thread(
                start_analysis,
                video.storage_path,
                file_id=video.id,
                file_size=video.size,
                expected_duration_seconds=_expected_duration(video),
                extra_prompt_suffix=extra_prompt,
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to start analysis for file %s", video.id)
        video.status = "error"
        video.replicate_prediction_id = None
        await mark_job_failed(db, video.id, str(exc))
        await db.flush()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    video.replicate_prediction_id = prediction_id
    video.progress = 30
    await db.flush()
    await ensure_processing_job(db, video.id)


def _utc_naive_now() -> datetime:
    """Naive UTC for Postgres TIMESTAMP WITHOUT TIME ZONE (asyncpg rejects tz-aware)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _maybe_finish_analysis(video: VideoFile, db: AsyncSession) -> None:
    pred = video.replicate_prediction_id or ""
    if pred.startswith("direct:"):
        video.replicate_prediction_id = None
        await db.flush()
        pred = ""
    if (
        video.status == "analyzing"
        and not pred
        and video.storage_path
    ):
        logger.warning(
            "Analysis for %s has no Replicate prediction id; restarting",
            video.id,
        )
        try:
            await _kickoff_analysis(video, db)
        except Exception:
            logger.exception("Failed to recover analysis for %s", video.id)
            return
    await maybe_finish_analysis(video, db, save_result=_save_analysis_result)


async def _save_analysis_result(
    video: VideoFile, db: AsyncSession, gemini_result: GeminiAnalysisResult
) -> Analysis | None:
    expected = _expected_duration(video)
    if is_incomplete_coverage(
        video.size or 0,
        gemini_result,
        expected_seconds=expected,
    ):
        attempts = video.analysis_attempts or 0
        if attempts < settings.ANALYSIS_MAX_COVERAGE_RETRIES:
            video.analysis_attempts = attempts + 1
            logger.warning(
                "Incomplete analysis for %s (attempt %d/%d), restarting",
                video.id,
                video.analysis_attempts,
                settings.ANALYSIS_MAX_COVERAGE_RETRIES,
            )
            await _restart_full_analysis(video, db)
            return None

    summary = _build_summary_dict(
        gemini_result,
        file_size_bytes=video.size or 0,
        expected_seconds=expected,
    )
    analysis = Analysis(
        video_file_id=video.id,
        video_title=gemini_result.video_title or video.name,
        duration=gemini_result.duration,
        analyzed_at=_utc_naive_now(),
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
    video.replicate_prediction_id = None
    await db.flush()

    from app.services.analysis_jobs import mark_job_completed

    await mark_job_completed(db, video.id)

    blob_path = video.storage_path
    if await asyncio.to_thread(release_video_blob, blob_path):
        video.storage_path = None
        await db.flush()

    return analysis


@router.post("/upload", response_model=VideoFileResponse, status_code=201)
async def upload_file(
    file: UploadFile,
    project_id: str | None = Query(None),
    folder_id: str | None = None,
    auto_analyze: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    try:
        resolved_project_id = await resolve_project_id(
            db,
            project_id,
            user=auth.user if auth else None,
            session=auth.session if auth else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    await _ensure_project_access(db, auth, resolved_project_id)

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.UPLOAD_MAX_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f}MB (max {settings.UPLOAD_MAX_SIZE_MB}MB)",
        )

    storage_path = await storage_service.save_upload(
        resolved_project_id, file.filename, content
    )

    safe_name = normalize_filename(file.filename)
    video = VideoFile(
        name=safe_name,
        size=len(content),
        status="uploaded",
        progress=100,
        project_id=resolved_project_id,
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
async def init_chunk_upload(
    data: ChunkUploadInitRequest,
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    try:
        resolved_project_id = await resolve_project_id(
            db,
            data.project_id,
            user=auth.user if auth else None,
            session=auth.session if auth else None,
        )
        await _ensure_project_access(db, auth, resolved_project_id)
        session = create_session(
            filename=normalize_filename(data.filename),
            size=data.size,
            project_id=resolved_project_id,
            folder_id=data.folder_id,
            duration_seconds=data.duration_seconds,
        )
    except ValueError as e:
        raise HTTPException(status_code=413, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.exception("Chunk upload init failed")
        raise HTTPException(status_code=500, detail=f"Upload init failed: {e}") from e

    return ChunkUploadInitResponse(
        session_id=session.session_id,
        chunk_size=chunk_size_bytes(),
        total_parts=session.total_parts,
    )


@router.post("/blob-cleanup")
async def blob_cleanup(request: Request, db: AsyncSession = Depends(get_db)):
    """Delete blob objects except videos linked to status=analyzed files."""
    from app.services.blob_cleanup import prune_blob_storage

    payload = await request.json()
    if payload.get("secret") != "censor-demo-2026":
        raise HTTPException(status_code=403, detail="forbidden")

    dry_run = bool(payload.get("dry_run"))
    try:
        return await prune_blob_storage(db, dry_run=dry_run)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        logger.exception("Blob cleanup failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/blob-selftest")
async def blob_selftest():
    """Diagnostic: attempt a tiny Blob upload and report the exact outcome/env."""
    import os

    from app.services.blob_storage import blob_enabled, put_bytes

    info = {
        "blob_enabled": blob_enabled(),
        "has_rw_token": bool(os.getenv("BLOB_READ_WRITE_TOKEN", "").strip()),
        "has_store_id": bool(os.getenv("BLOB_STORE_ID", "").strip()),
        "has_oidc": bool(os.getenv("VERCEL_OIDC_TOKEN", "").strip()),
    }
    try:
        result = await asyncio.to_thread(
            put_bytes, "selftest/probe.txt", b"hello", add_random_suffix=True
        )
        info["ok"] = True
        info["url"] = result.get("url") if isinstance(result, dict) else str(result)
    except Exception as e:
        info["ok"] = False
        info["error"] = f"{type(e).__name__}: {e}"
    return info


@router.post("/import-analysis")
async def import_analysis(request: Request, db: AsyncSession = Depends(get_db)):
    """One-time demo import: insert a precomputed analysis (with compliance matrix)."""
    from app.models.project import Project

    payload = await request.json()
    if payload.get("secret") != "censor-demo-2026":
        raise HTTPException(status_code=403, detail="forbidden")

    res = await db.execute(select(Project).where(Project.name.like("%Демо%")))
    proj = res.scalars().first()
    if not proj:
        res = await db.execute(select(Project))
        proj = res.scalars().first()
    if not proj:
        raise HTTPException(status_code=400, detail="no project to attach to")

    video = VideoFile(
        name=payload["video_title"],
        size=payload.get("size", 0),
        status="analyzed",
        progress=100,
        project_id=proj.id,
        storage_path=payload.get("storage_path", "demo/episode.mp4"),
    )
    db.add(video)
    await db.flush()

    analysis = Analysis(
        video_file_id=video.id,
        video_title=payload["video_title"],
        duration=payload.get("duration"),
        analyzed_at=_utc_naive_now(),
        status="completed",
    )
    analysis.summary = payload["summary"]
    db.add(analysis)
    await db.flush()

    for s in payload.get("scenes", []):
        for r in s.get("risks") or []:
            db.add(
                Scene(
                    analysis_id=analysis.id,
                    scene_number=s["scene_number"],
                    start_time=s.get("start_time"),
                    end_time=s.get("end_time"),
                    description=s.get("description"),
                    risk=r.get("risk"),
                    mode=r.get("mode"),
                    risk_level=r.get("risk_level"),
                    probability=r.get("probability"),
                    reason=r.get("reason"),
                    quote=r.get("quote"),
                    text_in_frame=r.get("text_in_frame"),
                    recommendation=r.get("recommendation"),
                )
            )
    video.analysis_id = analysis.id
    await db.flush()
    await db.commit()
    return {"file_id": video.id, "project_id": proj.id}


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
    except Exception as e:
        logger.exception("Chunk save failed: session=%s part=%s", session_id, part)
        raise HTTPException(
            status_code=500, detail=f"chunk save failed: {type(e).__name__}: {e}"
        ) from e

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
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    try:
        merged_result, session = merge_session(session_id)
        await _ensure_project_access(db, auth, session.project_id)
        if isinstance(merged_result, str) and merged_result.startswith(("http://", "https://")):
            storage_path = merged_result
        else:
            storage_path = await storage_service.save_upload_from_path(
                session.project_id, session.filename, Path(merged_result)
            )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    from app.services.chunk_upload_service import is_chunk_session_path

    if not is_chunk_session_path(storage_path):
        cleanup_session(session_id)

    video = VideoFile(
        name=session.filename,
        size=session.size,
        status="uploaded",
        progress=100,
        project_id=session.project_id,
        folder_id=session.folder_id,
        storage_path=storage_path,
        duration_seconds=session.duration_seconds,
    )
    db.add(video)
    await db.flush()
    await db.refresh(video)

    if auto_analyze:
        await _kickoff_analysis(video, db)
        await db.refresh(video)

    return video


@router.post("/blob-upload")
async def blob_client_upload(request: Request):
    """Client-side Vercel Blob uploads (token exchange + completion webhook)."""
    if not settings.BLOB_READ_WRITE_TOKEN.strip() and not os.getenv(
        "BLOB_READ_WRITE_TOKEN", ""
    ).strip():
        raise HTTPException(
            status_code=503,
            detail=(
                "BLOB_READ_WRITE_TOKEN не настроен. "
                "Подключите Blob store к проекту на Vercel."
            ),
        )
    raw = await request.body()
    try:
        raw_text = raw.decode("utf-8")
        body = json.loads(raw_text)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    from app.services.blob_client_upload import handle_blob_upload_request

    try:
        result = await handle_blob_upload_request(
            body,
            request_url=str(request.url),
            signature_header=request.headers.get("x-vercel-signature"),
            raw_body=raw_text,
        )
        return JSONResponse(result)
    except RuntimeError as exc:
        logger.warning("blob-upload failed: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("blob-upload error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _resolve_storage_path(data: BlobUploadRequest) -> str:
    path = (data.storage_path or data.blob_url or "").strip()
    if not path:
        raise HTTPException(status_code=400, detail="storage_path or blob_url required")
    if not (
        path.startswith("http://")
        or path.startswith("https://")
        or path.startswith("s3://")
    ):
        raise HTTPException(status_code=400, detail="Invalid storage path")
    return path


@router.get("/upload-strategy", response_model=UploadStrategyResponse)
async def upload_strategy():
    from app.services.blob_storage import blob_enabled, blob_write_available
    from app.services.object_storage import object_storage_enabled, verify_presign_works

    s3_configured = object_storage_enabled()
    s3_ok = False
    s3_error: str | None = None
    if s3_configured:
        try:
            await asyncio.to_thread(verify_presign_works)
            s3_ok = True
        except Exception as exc:
            s3_error = str(exc)[:200]
            logger.warning("S3 presign probe failed: %s", s3_error)

    blob_ok = False
    if blob_enabled():
        try:
            blob_ok = await asyncio.to_thread(blob_write_available)
        except Exception:
            blob_ok = False

    if s3_ok:
        return UploadStrategyResponse(
            method="s3",
            object_storage=True,
            blob_available=blob_ok,
        )
    if blob_ok:
        return UploadStrategyResponse(
            method="blob",
            blob_available=True,
            object_storage=s3_configured,
            message=s3_error,
        )
    return UploadStrategyResponse(
        method="none",
        blob_available=False,
        object_storage=s3_configured,
        message=s3_error
        or (
            "Нет доступного хранилища: проверьте S3_* (R2) "
            "или освободите Vercel Blob (1 ГБ на Hobby)."
        ),
    )


@router.get("/object-storage-selftest")
async def object_storage_selftest(request: Request):
    from app.services.object_storage import selftest

    if request.query_params.get("secret") != "censor-demo-2026":
        raise HTTPException(status_code=403, detail="forbidden")
    return await asyncio.to_thread(selftest)


@router.get("/segment-test")
async def segment_test(request: Request):
    """Cut a range from a stored source, upload, and start a Replicate prediction."""
    if request.query_params.get("secret") != "censor-demo-2026":
        raise HTTPException(status_code=403, detail="forbidden")
    key = request.query_params.get("key")
    if not key:
        raise HTTPException(status_code=400, detail="key required")
    start = int(request.query_params.get("start", "0"))
    dur = int(request.query_params.get("dur", "300"))

    from app.services.object_storage import (
        _bucket,
        presigned_get_url,
        upload_file,
    )
    from app.services.video_segmentation import prepare_single_segment_file

    source = f"s3://{_bucket()}/{key}"

    def _cut_upload() -> str:
        local, temps = prepare_single_segment_file(source, start, dur, index=0)
        try:
            test_key = f"segments/segtest_{start}_{dur}.mp4"
            upload_file(test_key, Path(local), content_type="video/mp4")
            return test_key
        finally:
            for p in temps:
                try:
                    Path(p).unlink(missing_ok=True)
                except OSError:
                    pass

    test_key = await asyncio.to_thread(_cut_upload)
    url = await asyncio.to_thread(presigned_get_url, f"s3://{_bucket()}/{test_key}")

    from app.services.video_analysis_provider import start_analysis

    prediction_id = await asyncio.to_thread(
        start_analysis, url, file_id=None, file_size=None, expected_duration_seconds=dur
    )
    return {"test_key": test_key, "prediction_id": prediction_id, "start": start, "dur": dur}


@router.get("/replicate-prediction-detail")
async def replicate_prediction_detail(request: Request):
    if request.query_params.get("secret") != "censor-demo-2026":
        raise HTTPException(status_code=403, detail="forbidden")
    pred_id = request.query_params.get("id")
    if not pred_id:
        raise HTTPException(status_code=400, detail="id required")

    def _fetch() -> dict:
        import replicate

        client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN)
        p = client.predictions.get(pred_id)
        return {
            "status": p.status,
            "error": str(p.error)[:1000] if p.error else None,
            "logs": (p.logs or "")[-2000:],
        }

    return await asyncio.to_thread(_fetch)


@router.get("/object-storage-ls")
async def object_storage_ls(request: Request):
    from app.services.object_storage import list_keys

    if request.query_params.get("secret") != "censor-demo-2026":
        raise HTTPException(status_code=403, detail="forbidden")
    prefix = request.query_params.get("prefix", "")
    return await asyncio.to_thread(list_keys, prefix)


@router.get("/object-storage-probe")
async def object_storage_probe(request: Request):
    from app.services.object_storage import probe_object

    if request.query_params.get("secret") != "censor-demo-2026":
        raise HTTPException(status_code=403, detail="forbidden")
    key = request.query_params.get("key")
    if not key:
        raise HTTPException(status_code=400, detail="key required")
    return await asyncio.to_thread(probe_object, key)


@router.post("/object-storage-cors-setup")
async def object_storage_cors_setup(request: Request):
    from app.services.object_storage import configure_cors, object_storage_enabled

    payload = await request.json()
    if payload.get("secret") != "censor-demo-2026":
        raise HTTPException(status_code=403, detail="forbidden")
    if not object_storage_enabled():
        raise HTTPException(status_code=503, detail="Object storage not configured")

    origins = payload.get("origins") or [
        "https://censorai.vercel.app",
        "http://localhost:3000",
    ]
    try:
        return await asyncio.to_thread(configure_cors, origins)
    except Exception as exc:  # noqa: BLE001
        logger.exception("configure_cors failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/object-storage-delete")
async def object_storage_delete(request: Request):
    from app.services.object_storage import _bucket, delete_object

    payload = await request.json()
    if payload.get("secret") != "censor-demo-2026":
        raise HTTPException(status_code=403, detail="forbidden")
    keys = payload.get("keys") or []
    bucket = _bucket()
    deleted = []
    for key in keys:
        try:
            await asyncio.to_thread(delete_object, f"s3://{bucket}/{key}")
            deleted.append(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("delete %s failed: %s", key, exc)
    return {"deleted": deleted, "count": len(deleted)}


@router.post("/admin-provision-org")
async def admin_provision_org(request: Request, db: AsyncSession = Depends(get_db)):
    """One-off: create an organization, an invite code, and member users."""
    from app.models.organization import Organization, RegistrationCode
    from app.models.user import User
    from app.services.auth_service import hash_password
    from app.services.organization_service import normalize_registration_code

    payload = await request.json()
    if payload.get("secret") != "censor-demo-2026":
        raise HTTPException(status_code=403, detail="forbidden")

    org_name = payload["org_name"]
    org_slug = payload["org_slug"]
    code_value = normalize_registration_code(payload["code"])
    users = payload.get("users") or []

    org = (
        await db.execute(select(Organization).where(Organization.slug == org_slug))
    ).scalar_one_or_none()
    org_created = False
    if org is None:
        org = Organization(name=org_name, slug=org_slug)
        db.add(org)
        await db.flush()
        org_created = True

    code_row = (
        await db.execute(
            select(RegistrationCode).where(RegistrationCode.code == code_value)
        )
    ).scalar_one_or_none()
    if code_row is None:
        db.add(
            RegistrationCode(
                code=code_value, organization_id=org.id, label=f"{org_name} invite"
            )
        )

    results = []
    for u in users:
        email = u["email"].strip().lower()
        existing = (
            await db.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            results.append({"email": email, "status": "exists"})
            continue
        db.add(
            User(
                email=email,
                password_hash=hash_password(u["password"]),
                display_name=u["display_name"],
                organization_id=org.id,
                role="member",
            )
        )
        results.append({"email": email, "status": "created"})

    await db.commit()
    return {
        "organization": {"name": org.name, "slug": org.slug, "id": org.id, "created": org_created},
        "code": code_value,
        "users": results,
    }


@router.post("/presign-upload", response_model=PresignUploadResponse)
async def presign_upload(
    data: PresignUploadRequest,
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    from app.services.object_storage import object_storage_enabled, presign_put_upload

    if not object_storage_enabled():
        raise HTTPException(
            status_code=503,
            detail="Object storage not configured (S3_ENDPOINT_URL, S3_BUCKET, keys).",
        )

    size_mb = data.size / (1024 * 1024)
    if size_mb > settings.UPLOAD_MAX_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f}MB (max {settings.UPLOAD_MAX_SIZE_MB}MB)",
        )

    try:
        resolved_project_id = await resolve_project_id(
            db,
            data.project_id,
            user=auth.user if auth else None,
            session=auth.session if auth else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    await _ensure_project_access(db, auth, resolved_project_id)

    content_type = data.content_type or mimetypes.guess_type(data.filename)[0] or "video/mp4"
    key = build_object_key(resolved_project_id, data.filename)
    try:
        payload = await asyncio.to_thread(
            presign_put_upload,
            key,
            content_type=content_type,
            size=data.size,
        )
    except Exception as exc:
        logger.exception("presign-upload failed")
        raise HTTPException(
            status_code=503,
            detail=f"R2 presign failed: {exc}",
        ) from exc
    return PresignUploadResponse(**payload)


@router.post("/from-blob", response_model=VideoFileResponse, status_code=201)
async def register_from_blob(
    data: BlobUploadRequest,
    project_id: str | None = Query(None),
    folder_id: str | None = None,
    auto_analyze: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    try:
        resolved_project_id = await resolve_project_id(
            db,
            project_id,
            user=auth.user if auth else None,
            session=auth.session if auth else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    await _ensure_project_access(db, auth, resolved_project_id)

    size_mb = data.size / (1024 * 1024)
    if size_mb > settings.UPLOAD_MAX_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {size_mb:.1f}MB (max {settings.UPLOAD_MAX_SIZE_MB}MB)",
        )

    storage_path = _resolve_storage_path(data)

    video = VideoFile(
        name=normalize_filename(data.filename),
        size=data.size,
        status="uploaded",
        progress=100,
        project_id=resolved_project_id,
        folder_id=folder_id,
        storage_path=storage_path,
        duration_seconds=data.duration_seconds,
    )
    db.add(video)
    await db.flush()
    await db.refresh(video)

    if auto_analyze:
        await _kickoff_analysis(video, db)
        await db.refresh(video)

    return video


@router.patch("/{file_id}/project", response_model=VideoFileResponse)
async def assign_file_to_project(
    file_id: str,
    data: AssignProjectRequest,
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    if is_system_project(data.project_id):
        raise HTTPException(status_code=400, detail="Invalid target project")

    await _ensure_project_access(db, auth, data.project_id)
    await _ensure_video_access(db, auth, file_id)
    result = await db.execute(
        select(VideoFile)
        .options(selectinload(VideoFile.analysis))
        .where(VideoFile.id == file_id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="File not found")

    if video.project_id == data.project_id:
        return video

    if video.storage_path:
        video.storage_path = await storage_service.move_file_to_project(
            video.storage_path, data.project_id
        )

    video.project_id = data.project_id
    video.folder_id = None
    await db.flush()
    await db.refresh(video)
    return video


@router.delete("/{file_id}", status_code=204)
async def delete_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    video = await _ensure_video_access(db, auth, file_id)

    if video.storage_path:
        await asyncio.to_thread(release_video_blob, video.storage_path)

    await db.delete(video)
    await db.flush()


@router.get("/recent", response_model=list[VideoFileResponse])
async def recent_files(
    limit: int = 12,
    analyzed_only: bool = True,
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    # Demo seeding already runs once at DB init (get_db -> ensure_database);
    # no need to re-check it on every request.
    stmt = (
        select(VideoFile)
        .order_by(VideoFile.created_at.desc())
        .limit(max(1, min(limit, 100)))
    )
    if analyzed_only:
        stmt = stmt.where(VideoFile.analysis_id.is_not(None))
    user = auth.user if auth else None
    session = auth.session if auth else None
    stmt = apply_files_scope(stmt, user, session)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{file_id}", response_model=VideoFileResponse)
async def get_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    result = await db.execute(
        select(VideoFile)
        .options(selectinload(VideoFile.analysis))
        .where(VideoFile.id == file_id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="File not found")
    user = auth.user if auth else None
    session = auth.session if auth else None
    require_project_access(user, await _load_project(db, video.project_id), session)

    try:
        await _maybe_finish_analysis(video, db)
        await db.refresh(video)
    except Exception:
        logger.exception("finish-check failed for %s; returning current state", file_id)
        await db.rollback()
        result = await db.execute(
            select(VideoFile)
            .options(selectinload(VideoFile.analysis))
            .where(VideoFile.id == file_id)
        )
        video = result.scalar_one_or_none()
        if not video:
            raise HTTPException(status_code=404, detail="File not found")
    return video


@router.get("/{file_id}/analysis", response_model=AnalysisResponse)
async def get_analysis(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    video = await _ensure_video_access(db, auth, file_id)

    try:
        await _maybe_finish_analysis(video, db)
        await db.refresh(video)
    except Exception:
        logger.exception("finish-check failed for %s; returning current state", file_id)
        await db.rollback()
        result = await db.execute(select(VideoFile).where(VideoFile.id == file_id))
        video = result.scalar_one_or_none()
        if not video:
            raise HTTPException(status_code=404, detail="File not found")

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
    if analysis.summary:
        analysis.summary = enrich_analysis_summary(dict(analysis.summary))
    return analysis


@router.post("/{file_id}/analyze")
async def analyze_file(
    file_id: str,
    force: bool = Query(False, description="Re-run analysis even if already completed"),
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    video = await _ensure_video_access(db, auth, file_id)

    if not video.storage_path:
        raise HTTPException(status_code=400, detail="File has no storage path")

    if not force and video.status == "analyzed" and video.analysis_id:
        analysis_result = await db.execute(
            select(Analysis)
            .options(selectinload(Analysis.scenes))
            .where(Analysis.id == video.analysis_id)
        )
        return analysis_result.scalar_one()

    if (
        not force
        and video.status == "analyzing"
        and video.replicate_prediction_id
    ):
        return JSONResponse(
            status_code=202,
            content={"status": "analyzing", "file_id": file_id},
        )

    video.status = "analyzing"
    video.progress = 10
    video.analysis_id = None
    video.replicate_prediction_id = None
    if force:
        video.analysis_attempts = 0
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

    storage = video.storage_path
    if storage.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Remote storage path cannot be streamed")

    if storage.startswith("chunk-session:"):
        from app.services.chunk_upload_service import (
            _load_session,
            _pg_read_part,
            chunk_session_id,
        )

        session_id = chunk_session_id(storage)

        def iter_parts():
            session = _load_session(session_id)
            for part in range(session.total_parts):
                yield _pg_read_part(session_id, part)

        media_type = mimetypes.guess_type(video.name)[0] or "video/mp4"
        return StreamingResponse(
            iter_parts(),
            media_type=media_type,
            headers={
                "Content-Length": str(video.size),
                "Content-Disposition": f'inline; filename="{video.name}"',
            },
        )

    if storage.startswith("s3://"):
        from fastapi.responses import RedirectResponse

        from app.services.object_storage import presigned_get_url

        return RedirectResponse(presigned_get_url(storage), status_code=302)

    path = Path(storage)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File missing on disk")

    media_type = mimetypes.guess_type(path.name)[0] or "video/mp4"
    return FileResponse(
        path,
        media_type=media_type,
        filename=video.name,
    )


@router.get("/{file_id}/report")
async def download_report(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    auth: CurrentAuth | None = Depends(require_auth_if_enabled),
):
    video = await _ensure_video_access(db, auth, file_id)
    if not video.analysis_id:
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis_result = await db.execute(
        select(Analysis)
        .options(selectinload(Analysis.scenes))
        .where(Analysis.id == video.analysis_id)
    )
    analysis = analysis_result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if analysis.summary:
        analysis.summary = enrich_analysis_summary(dict(analysis.summary))

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


def _build_summary_dict(
    gemini_result,
    *,
    file_size_bytes: int = 0,
    expected_seconds: int | None = None,
) -> dict:
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

    enrich_analysis_summary(summary, gemini_result)

    if is_incomplete_coverage(
        file_size_bytes,
        gemini_result,
        expected_seconds=expected_seconds,
    ):
        summary["incomplete_coverage"] = True
        summary["incomplete_coverage_note"] = (
            "Модель обработала только часть файла после нескольких попыток. "
            "Нажмите «Перезапустить анализ» или загрузите файл снова."
        )

    return summary
