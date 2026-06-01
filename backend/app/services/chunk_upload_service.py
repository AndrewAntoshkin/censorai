"""Assemble large uploads from small chunks (Vercel 4.5MB request limit)."""

from __future__ import annotations

import json
import logging
import os
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.upload_session import UploadChunkSession
from app.services.blob_storage import blob_enabled, fetch_bytes, put_bytes

logger = logging.getLogger(__name__)

CHUNK_SIZE_BYTES = 3 * 1024 * 1024  # 3 MB — safely under Vercel body limit
SESSION_TTL = timedelta(hours=2)


@dataclass
class UploadSession:
    session_id: str
    filename: str
    size: int
    project_id: str
    total_parts: int
    folder_id: str | None
    received_parts: set[int]
    part_urls: dict[int, str] = field(default_factory=dict)
    duration_seconds: float | None = None

    @property
    def dir(self) -> Path:
        return _sessions_root() / self.session_id

    def meta_path(self) -> Path:
        return self.dir / "meta.json"

    def part_path(self, part: int) -> Path:
        return self.dir / f"part-{part:05d}"

    def _part_blob_path(self, part: int) -> str:
        return f"chunks/{self.session_id}/part-{part:05d}"


def _use_db_sessions() -> bool:
    return "postgres" in settings.DATABASE_URL


def _use_blob_parts() -> bool:
    return blob_enabled() and bool(os.getenv("VERCEL"))


def _sessions_root() -> Path:
    root = Path(settings.UPLOAD_DIR) / "_chunk_sessions"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sync_engine():
    connect_args: dict = {}
    if "postgres" in settings.DATABASE_URL_SYNC:
        connect_args = {"sslmode": "require"}
    return create_engine(settings.DATABASE_URL_SYNC, connect_args=connect_args)


def _session_to_dict(session: UploadSession) -> dict:
    return {
        "session_id": session.session_id,
        "filename": session.filename,
        "size": session.size,
        "project_id": session.project_id,
        "folder_id": session.folder_id,
        "total_parts": session.total_parts,
        "received_parts": sorted(session.received_parts),
        "part_urls": {str(k): v for k, v in session.part_urls.items()},
        "duration_seconds": session.duration_seconds,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _session_from_dict(data: dict) -> UploadSession:
    created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) - created_at > SESSION_TTL:
        raise FileNotFoundError(f"Upload session expired: {data['session_id']}")

    part_urls = {int(k): v for k, v in (data.get("part_urls") or {}).items()}
    return UploadSession(
        session_id=data["session_id"],
        filename=data["filename"],
        size=data["size"],
        project_id=data["project_id"],
        total_parts=data["total_parts"],
        folder_id=data.get("folder_id"),
        received_parts=set(data.get("received_parts", [])),
        part_urls=part_urls,
        duration_seconds=data.get("duration_seconds"),
    )


def _db_upsert(session: UploadSession) -> None:
    engine = _sync_engine()
    with Session(engine) as db:
        row = db.get(UploadChunkSession, session.session_id)
        if row is None:
            row = UploadChunkSession(
                id=session.session_id,
                filename=session.filename,
                size=session.size,
                project_id=session.project_id,
                folder_id=session.folder_id,
                total_parts=session.total_parts,
            )
            db.add(row)
        row.received_parts_json = json.dumps(sorted(session.received_parts))
        row.part_urls_json = json.dumps({str(k): v for k, v in session.part_urls.items()})
        row.duration_seconds = session.duration_seconds
        db.commit()


def _db_load(session_id: str) -> UploadSession:
    engine = _sync_engine()
    with Session(engine) as db:
        row = db.get(UploadChunkSession, session_id)
        if row is None:
            raise FileNotFoundError(f"Upload session not found: {session_id}")

        created = row.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created > SESSION_TTL:
            db.delete(row)
            db.commit()
            raise FileNotFoundError(f"Upload session expired: {session_id}")

        return UploadSession(
            session_id=row.id,
            filename=row.filename,
            size=row.size,
            project_id=row.project_id,
            total_parts=row.total_parts,
            folder_id=row.folder_id,
            received_parts=set(json.loads(row.received_parts_json or "[]")),
            part_urls={int(k): v for k, v in json.loads(row.part_urls_json or "{}").items()},
            duration_seconds=row.duration_seconds,
        )


def _db_delete(session_id: str) -> None:
    engine = _sync_engine()
    with Session(engine) as db:
        row = db.get(UploadChunkSession, session_id)
        if row:
            db.delete(row)
            db.commit()


def _save_session(session: UploadSession) -> None:
    if _use_db_sessions():
        _db_upsert(session)
        return

    session.dir.mkdir(parents=True, exist_ok=True)
    session.meta_path().write_bytes(
        json.dumps(_session_to_dict(session), ensure_ascii=False).encode("utf-8")
    )


def _load_session(session_id: str) -> UploadSession:
    if _use_db_sessions():
        return _db_load(session_id)

    meta_path = _sessions_root() / session_id / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"Upload session not found: {session_id}")

    data = json.loads(meta_path.read_text(encoding="utf-8"))
    return _session_from_dict(data)


def create_session(
    filename: str,
    size: int,
    project_id: str,
    folder_id: str | None = None,
    duration_seconds: float | None = None,
) -> UploadSession:
    size_mb = size / (1024 * 1024)
    if size_mb > settings.UPLOAD_MAX_SIZE_MB:
        raise ValueError(
            f"File too large: {size_mb:.1f}MB (max {settings.UPLOAD_MAX_SIZE_MB}MB)"
        )

    if _use_blob_parts() and not blob_enabled():
        raise RuntimeError(
            "BLOB_READ_WRITE_TOKEN or BLOB_STORE_ID+VERCEL_OIDC_TOKEN required for uploads on Vercel"
        )

    total_parts = max(1, (size + CHUNK_SIZE_BYTES - 1) // CHUNK_SIZE_BYTES)
    session = UploadSession(
        session_id=str(uuid.uuid4()),
        filename=filename,
        size=size,
        project_id=project_id,
        total_parts=total_parts,
        folder_id=folder_id,
        received_parts=set(),
        duration_seconds=duration_seconds,
    )
    _save_session(session)
    return session


def save_part(session_id: str, part: int, content: bytes) -> UploadSession:
    session = _load_session(session_id)
    if part < 0 or part >= session.total_parts:
        raise ValueError(f"Invalid part index: {part}")

    max_part_size = CHUNK_SIZE_BYTES
    if part == session.total_parts - 1:
        remaining = session.size - CHUNK_SIZE_BYTES * (session.total_parts - 1)
        max_part_size = max(1, remaining)

    if len(content) > max_part_size + 1024:
        raise ValueError(f"Chunk {part} too large: {len(content)} bytes")

    if _use_blob_parts():
        result = put_bytes(
            session._part_blob_path(part),
            content,
            content_type="application/octet-stream",
        )
        session.part_urls[part] = result["url"]
    else:
        session.dir.mkdir(parents=True, exist_ok=True)
        session.part_path(part).write_bytes(content)

    session.received_parts.add(part)
    _save_session(session)
    return session


def merge_session(session_id: str) -> tuple[str | Path, UploadSession]:
    session = _load_session(session_id)
    missing = [i for i in range(session.total_parts) if i not in session.received_parts]
    if missing:
        raise ValueError(f"Missing chunks: {missing[:5]}")

    if _use_blob_parts():
        merged = bytearray()
        for part in range(session.total_parts):
            url = session.part_urls.get(part)
            if not url:
                raise ValueError(f"Missing blob URL for chunk {part}")
            merged.extend(fetch_bytes(url))

        if len(merged) != session.size:
            raise ValueError(
                f"Assembled size mismatch: got {len(merged)}, expected {session.size}"
            )

        ext = "mp4"
        if "." in session.filename:
            ext = session.filename.rsplit(".", 1)[-1].lower() or "mp4"
        final_path = f"videos/{uuid.uuid4()}.{ext}"
        result = put_bytes(
            final_path,
            bytes(merged),
            content_type="video/mp4",
            add_random_suffix=True,
        )
        cleanup_session(session_id)
        return result["url"], session

    merged_path = session.dir / "merged.bin"
    with merged_path.open("wb") as out:
        for part in range(session.total_parts):
            out.write(session.part_path(part).read_bytes())

    if merged_path.stat().st_size != session.size:
        raise ValueError(
            f"Assembled size mismatch: got {merged_path.stat().st_size}, "
            f"expected {session.size}"
        )

    return merged_path, session


def cleanup_session(session_id: str) -> None:
    if _use_db_sessions():
        _db_delete(session_id)
    session_dir = _sessions_root() / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)


def chunk_size_bytes() -> int:
    return CHUNK_SIZE_BYTES
