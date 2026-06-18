#!/usr/bin/env python3
"""Local probe: test Gemini models on Replicate with a short video.

Requires REPLICATE_API_TOKEN in backend/.env.secrets (or env).

  cd backend && .venv/bin/python ../scripts/replicate_model_probe.py
  cd backend && .venv/bin/python ../scripts/replicate_model_probe.py --models google/gemini-2.5-flash
"""
from __future__ import annotations

import argparse
import base64
import mimetypes
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env")
load_dotenv(BACKEND / ".env.secrets", override=True)

import replicate
from app.core.config import settings

DEFAULT_MODELS = [
    "google/gemini-3.5-flash",
    "google/gemini-3-flash",
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro",
    "google/gemini-2.0-flash",
]

SAMPLE_URL = (
    "https://storage.googleapis.com/cloud-samples-data/"
    "generative-ai/video/ad_copy_from_video.mp4"
)


def make_tiny_mp4(path: Path, seconds: int = 10) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=5",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440",
            "-t",
            str(seconds),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(path),
        ],
        check=True,
    )


def video_uri(path: Path | None, use_url: bool) -> str:
    if use_url:
        return SAMPLE_URL
    assert path is not None
    content_type = mimetypes.guess_type(str(path))[0] or "video/mp4"
    raw = path.read_bytes()
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{content_type};base64,{encoded}"


def build_input(model: str, video: str) -> dict:
    inp: dict = {
        "prompt": "Опиши это видео одним предложением на русском.",
        "videos": [video],
        "temperature": 0.2,
        "max_output_tokens": 1024,
    }
    if "3.5-flash" in model or model.endswith("gemini-3-flash"):
        inp["video_fps"] = 1
    elif "2.5" in model:
        inp["thinking_budget"] = 0
    return inp


def probe_model(client: replicate.Client, model: str, video: str, wait_s: int) -> dict:
    out: dict = {"model": model}
    try:
        pred = client.predictions.create(model=model, input=build_input(model, video))
        out["prediction_id"] = pred.id
        deadline = time.time() + wait_s
        while time.time() < deadline:
            pred = client.predictions.get(pred.id)
            out["status"] = pred.status
            if pred.status in {"succeeded", "failed", "canceled"}:
                out["error"] = str(pred.error) if pred.error else None
                out["logs"] = (pred.logs or "")[-1200:]
                if pred.status == "succeeded":
                    raw = pred.output
                    if isinstance(raw, list):
                        out["output"] = "".join(str(x) for x in raw)[:400]
                    else:
                        out["output"] = str(raw)[:400]
                break
            time.sleep(3)
        else:
            out["status"] = out.get("status", "timeout")
            out["error"] = out.get("error") or f"timeout after {wait_s}s"
    except Exception as exc:
        out["status"] = "exception"
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe Replicate Gemini models with video")
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Replicate model slugs",
    )
    parser.add_argument("--wait", type=int, default=90, help="Max seconds per model")
    parser.add_argument(
        "--url",
        action="store_true",
        help="Use public sample URL instead of generated inline MP4",
    )
    args = parser.parse_args()

    token = settings.REPLICATE_API_TOKEN.strip()
    if not token:
        print(
            "REPLICATE_API_TOKEN не задан.\n"
            "Скопируйте r8_… из Vercel → backend/.env.secrets и запустите снова.",
            file=sys.stderr,
        )
        sys.exit(1)

    tmp: Path | None = None
    if args.url:
        video = video_uri(None, use_url=True)
        print(f"video: public URL ({SAMPLE_URL[:60]}…)")
    else:
        tmp = Path(tempfile.gettempdir()) / "replicate_probe_10s.mp4"
        make_tiny_mp4(tmp, seconds=10)
        mb = tmp.stat().st_size / 1024 / 1024
        video = video_uri(tmp, use_url=False)
        print(f"video: inline {mb:.1f} MB ({tmp})")

    client = replicate.Client(api_token=token)
    results = []
    for model in args.models:
        print(f"\n--- {model} ---", flush=True)
        r = probe_model(client, model, video, args.wait)
        results.append(r)
        print(f"  status: {r.get('status')}")
        if r.get("prediction_id"):
            print(f"  id: {r['prediction_id']}")
        if r.get("error"):
            print(f"  error: {str(r['error'])[:250]}")
        if r.get("output"):
            print(f"  output: {r['output'][:200]}")
        if r.get("logs"):
            tail = r["logs"].strip().splitlines()[-3:]
            print("  logs:", " | ".join(tail))

    ok = sum(1 for r in results if r.get("status") == "succeeded")
    print(f"\n=== {ok}/{len(results)} succeeded ===")
    if tmp and tmp.exists():
        tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
