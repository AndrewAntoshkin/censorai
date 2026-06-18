#!/usr/bin/env python3
"""Probe non-Gemini Replicate video models via prod debug-job endpoint."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

BASE = os.environ.get("BASE", "https://censorai.vercel.app")
DEBUG_SECRET = os.environ.get("DEBUG_SECRET", "censor-demo-2026")

DEFAULT_MODELS = [
    "chenxwh/cogvlm2-video",
    "lucataco/qwen2-vl-7b-instruct",
]

SAMPLE_URL = (
    "https://storage.googleapis.com/cloud-samples-data/"
    "generative-ai/video/ad_copy_from_video.mp4"
)


def post(payload: dict, timeout: int = 300) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}/api/files/debug-job",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def main() -> int:
    models = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_MODELS
    wait = min(int(os.environ.get("WAIT_SECONDS", "120")), 180)

    print(f"[probe] base={BASE} models={models} wait={wait}s", flush=True)
    t0 = time.time()
    try:
        result = post(
            {
                "secret": DEBUG_SECRET,
                "models": models,
                "video_url": SAMPLE_URL,
                "prompt": "Опиши это видео одним предложением на русском.",
                "wait_seconds": wait,
            },
            timeout=wait * len(models) + 60,
        )
    except Exception as exc:
        print(f"[probe] request failed: {exc}", flush=True)
        return 1

    print(f"[probe] done in {time.time() - t0:.1f}s", flush=True)
    print(f"video: {result.get('video_url', SAMPLE_URL)[:80]}…", flush=True)

    ok = 0
    for r in result.get("results") or []:
        status = r.get("status")
        if status == "succeeded":
            ok += 1
        print(f"\n--- {r.get('model')} ---", flush=True)
        print(f"  status: {status}", flush=True)
        if r.get("prediction_id"):
            print(f"  id: {r['prediction_id']}", flush=True)
        if r.get("error"):
            print(f"  error: {str(r['error'])[:350]}", flush=True)
        if r.get("output_preview"):
            print(f"  output: {r['output_preview'][:300]}", flush=True)
        if r.get("logs"):
            tail = r["logs"].strip().splitlines()[-4:]
            print("  logs:", " | ".join(tail), flush=True)

    total = len(result.get("results") or [])
    print(f"\n=== SUMMARY: {ok}/{total} succeeded ===", flush=True)
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
