#!/usr/bin/env python3
"""Run Qwen2-VL on a prod video file with CensorAI analysis prompt."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "backend/app/services/analysis_prompts.py"
DEFAULT_FILE_ID = "446c0ea5-3356-4616-b4e9-c97d97cfba0a"  # generation-eb061ad0…mp4
DEFAULT_BASE = os.environ.get(
    "BASE",
    "https://censorai-l6zdevlil-andrewantoshkin-gmailcoms-projects.vercel.app",
)
DEBUG_SECRET = os.environ.get("DEBUG_SECRET", "censor-demo-2026")
MODEL = "lucataco/qwen2-vl-7b-instruct"


def load_prompt() -> str:
    text = PROMPT_PATH.read_text(encoding="utf-8")
    marker = 'VIDEO_ANALYSIS_PROMPT = """'
    start = text.index(marker) + len(marker)
    end = text.index('"""', start)
    return text[start:end]


def main() -> int:
    file_id = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE_ID
    prompt = load_prompt()
    wait_seconds = int(os.environ.get("WAIT_SECONDS", "240"))

    payload = {
        "secret": DEBUG_SECRET,
        "models": [MODEL],
        "file_id": file_id,
        "prompt": prompt,
        "wait_seconds": wait_seconds,
    }

    print(f"base={DEFAULT_BASE}", flush=True)
    print(f"file_id={file_id}", flush=True)
    print(f"model={MODEL}", flush=True)
    print(f"prompt_chars={len(prompt)} wait={wait_seconds}s", flush=True)

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{DEFAULT_BASE}/api/files/debug-job",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=wait_seconds + 120) as resp:
        result = json.loads(resp.read())

    print(f"video_url={result.get('video_url', '')[:120]}…", flush=True)
    entry = (result.get("results") or [{}])[0]
    print(f"status={entry.get('status')} id={entry.get('prediction_id')}", flush=True)
    if entry.get("error"):
        print(f"error={entry['error']}", flush=True)
    if entry.get("logs"):
        print("--- logs tail ---", flush=True)
        print(entry["logs"][-1500:], flush=True)

    output = entry.get("output_preview") or ""
    print("--- output ---", flush=True)
    print(output, flush=True)

    out_path = Path(tempfile.gettempdir()) / f"qwen_probe_{file_id[:8]}.json"
    out_path.write_text(
        json.dumps(
            {
                "file_id": file_id,
                "model": MODEL,
                "prediction_id": entry.get("prediction_id"),
                "status": entry.get("status"),
                "error": entry.get("error"),
                "output": output,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"saved={out_path}", flush=True)
    return 0 if entry.get("status") == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
