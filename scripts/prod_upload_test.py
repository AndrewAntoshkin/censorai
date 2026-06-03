#!/usr/bin/env python3
"""Upload a video to production via chunk API and poll until analyzed or error."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

CHUNK_SIZE = 3 * 1024 * 1024
DEFAULT_BASE = "https://censorai.vercel.app"
POLL_INTERVAL_SEC = 10
MAX_WAIT_SEC = 60 * 60


def upload_video(base: str, video_path: Path, project_id: str | None = None) -> dict:
    size = video_path.stat().st_size
    total_parts = max(1, (size + CHUNK_SIZE - 1) // CHUNK_SIZE)

    with httpx.Client(base_url=base.rstrip("/"), timeout=httpx.Timeout(600.0, connect=60.0)) as client:
        if not project_id:
            proj = client.post(
                "/api/projects",
                json={"name": f"Prod test {time.strftime('%Y-%m-%d %H:%M')}"},
            )
            proj.raise_for_status()
            project_id = proj.json()["id"]
            print(f"project_id={project_id}")

        init = client.post(
            "/api/files/upload-chunks/init",
            json={
                "filename": video_path.name,
                "size": size,
                "project_id": project_id,
            },
        )
        init.raise_for_status()
        data = init.json()
        session_id = data["session_id"]
        print(f"session_id={session_id} parts={total_parts} size_mb={size / (1024*1024):.1f}")

        for part in range(total_parts):
            start = part * CHUNK_SIZE
            chunk = video_path.read_bytes()[start : start + CHUNK_SIZE]
            r = client.put(
                f"/api/files/upload-chunks/{session_id}/parts/{part}",
                content=chunk,
                headers={"Content-Type": "application/octet-stream"},
            )
            r.raise_for_status()
            print(f"  chunk {part + 1}/{total_parts} ok", flush=True)

        complete = client.post(
            f"/api/files/upload-chunks/{session_id}/complete",
            params={"auto_analyze": "1"},
        )
        complete.raise_for_status()
        file_info = complete.json()
        print(f"upload complete file_id={file_info['id']} status={file_info.get('status')}")
        return file_info


def poll_until_done(base: str, file_id: str) -> dict:
    deadline = time.time() + MAX_WAIT_SEC
    with httpx.Client(base_url=base.rstrip("/"), timeout=httpx.Timeout(600.0, connect=60.0)) as client:
        while time.time() < deadline:
            r = client.get(f"/api/files/{file_id}")
            if r.status_code >= 500:
                print(f"poll {r.status_code}, retry…")
                time.sleep(POLL_INTERVAL_SEC)
                continue
            r.raise_for_status()
            data = r.json()
            status = data.get("status")
            progress = data.get("progress")
            pred = data.get("replicate_prediction_id")
            print(
                f"  {time.strftime('%H:%M:%S')} status={status} progress={progress} pred={pred or '-'}",
                flush=True,
            )
            if status == "analyzed":
                return data
            if status == "error":
                raise RuntimeError(f"analysis failed: {json.dumps(data, ensure_ascii=False)[:500]}")
            time.sleep(POLL_INTERVAL_SEC)
    raise TimeoutError(f"timed out after {MAX_WAIT_SEC}s")


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BASE
    video = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[1] / "backend/eval/clips/kuhnya-s01e01.mp4"
    if not video.is_file():
        print(f"Video not found: {video}", file=sys.stderr)
        return 1

    print(f"base={base} video={video}")
    file_info = upload_video(base, video)
    file_id = file_info["id"]
    print(f"\nPolling analysis for {file_id}…")
    final = poll_until_done(base, file_id)
    analysis_id = final.get("analysis_id")
    print(f"\nDONE file_id={file_id} analysis_id={analysis_id}")
    print(f"View: {base}/file/{file_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
