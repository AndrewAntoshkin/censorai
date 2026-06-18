#!/usr/bin/env python3
"""Probe direct Google Gemini API on a prod video with CensorAI prompt."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

import google.generativeai as genai
import httpx

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env")
load_dotenv(BACKEND / ".env.secrets", override=True)

from app.core.config import settings
from app.services.analysis_coverage import full_coverage_prompt_suffix
from app.services.analysis_prompts import VIDEO_ANALYSIS_PROMPT
from app.services.gemini_service import gemini_service
from app.services.object_storage import presigned_get_url

DEFAULT_STORAGE = (
    "s3://censorai-videos/projects/cf419b69-9195-49db-901d-73f06bb751fd/"
    "0e31ebc4-ed94-49b8-9830-a87e148da2b5.mp4"
)
DEFAULT_DURATION = 150


def main() -> int:
    storage = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_STORAGE
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_DURATION
    model_name = (settings.GEMINI_MODEL or "gemini-2.5-flash").strip()

    api_key = settings.GEMINI_API_KEY.strip()
    if not api_key:
        print("GEMINI_API_KEY не задан в backend/.env.secrets", file=sys.stderr)
        return 1

    genai.configure(api_key=api_key)
    prompt = VIDEO_ANALYSIS_PROMPT + full_coverage_prompt_suffix(duration)

    print(f"model={model_name} storage={storage}", flush=True)
    print(f"prompt_chars={len(prompt)} duration={duration}s", flush=True)

    url = presigned_get_url(storage)
    tmp = Path(tempfile.gettempdir()) / "gemini_direct_probe.mp4"
    print("downloading video...", flush=True)
    with httpx.Client(timeout=httpx.Timeout(600.0, connect=60.0), follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        tmp.write_bytes(resp.content)
    print(f"downloaded {tmp.stat().st_size / 1024 / 1024:.1f} MB", flush=True)

    print("uploading to Gemini Files API...", flush=True)
    video_file = genai.upload_file(str(tmp))
    deadline = time.time() + 600
    while video_file.state.name == "PROCESSING":
        if time.time() > deadline:
            print("Gemini file processing timeout", file=sys.stderr)
            return 1
        time.sleep(3)
        video_file = genai.get_file(video_file.name)
        print(f"  file state={video_file.state.name}", flush=True)
    if video_file.state.name != "ACTIVE":
        print(f"Gemini file not active: {video_file.state.name}", file=sys.stderr)
        return 1

    model = genai.GenerativeModel(model_name)
    print("generating analysis...", flush=True)
    t0 = time.time()
    response = model.generate_content(
        [video_file, prompt],
        generation_config=genai.GenerationConfig(
            temperature=0.2,
            max_output_tokens=8192,
            response_mime_type="application/json",
        ),
        request_options={"timeout": 600},
    )
    elapsed = time.time() - t0
    raw = (response.text or "").strip()
    print(f"response in {elapsed:.1f}s, chars={len(raw)}", flush=True)

    out_path = Path(tempfile.gettempdir()) / "gemini_direct_probe_result.json"
    try:
        parsed = gemini_service._parse_response(raw)
        data = parsed.model_dump()
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"parsed OK scenes={len(data.get('scenes') or [])}", flush=True)
        print(f"title={data.get('video_title')}", flush=True)
        print(f"rating={data.get('recommended_age_rating')}", flush=True)
        if data.get("scenes"):
            s0 = data["scenes"][0]
            print(
                f"first_scene={s0.get('scene_number')} "
                f"{s0.get('start_time')}-{s0.get('end_time')} "
                f"risks={len(s0.get('risks') or [])}",
                flush=True,
            )
    except Exception as exc:
        out_path = Path(tempfile.gettempdir()) / "gemini_direct_probe_raw.txt"
        out_path.write_text(raw, encoding="utf-8")
        print(f"parse failed: {exc}", flush=True)
        print(raw[:2000], flush=True)

    print(f"saved={out_path}", flush=True)
    try:
        genai.delete_file(video_file.name)
    except Exception:
        pass
    tmp.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
