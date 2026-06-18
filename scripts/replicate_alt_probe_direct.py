#!/usr/bin/env python3
"""Direct Replicate probe for CogVLM2-Video and Qwen2-VL (needs REPLICATE_API_TOKEN)."""

from __future__ import annotations

import argparse
import os
import sys
import time

import replicate

DEFAULT_MODELS = [
    "chenxwh/cogvlm2-video",
    "lucataco/qwen2-vl-7b-instruct",
]

VERSION_OVERRIDES = {
    "chenxwh/cogvlm2-video": (
        "9da7e9a554d36bb7b5fec36b43b00e4616dc1e819bc963ded8e053d8d8196cb5"
    ),
    "lucataco/qwen2-vl-7b-instruct": (
        "bf57361c75677fc33d480d0c5f02926e621b2caa2000347cb74aeae9d2ca07ee"
    ),
}

SAMPLE_URL = (
    "https://storage.googleapis.com/cloud-samples-data/"
    "generative-ai/video/ad_copy_from_video.mp4"
)

PROMPT = "Опиши это видео одним предложением на русском."


def build_input(model: str, video_url: str) -> dict:
    slug = model.rsplit("/", 1)[-1]
    if "cogvlm2-video" in slug:
        return {
            "input_video": video_url,
            "prompt": PROMPT,
            "temperature": 0.1,
            "top_p": 0.1,
            "max_new_tokens": 512,
        }
    if "qwen2-vl" in slug:
        return {
            "media": video_url,
            "prompt": PROMPT,
            "max_new_tokens": 256,
        }
    raise ValueError(f"unsupported model: {model}")


def probe(client: replicate.Client, model: str, video_url: str, wait_s: int) -> dict:
    out: dict = {"model": model}
    try:
        inp = build_input(model, video_url)
        version_id = VERSION_OVERRIDES.get(model)
        if version_id:
            pred = client.predictions.create(version=version_id, input=inp)
        else:
            pred = client.predictions.create(model=model, input=inp)
        out["prediction_id"] = pred.id
        deadline = time.time() + wait_s
        while time.time() < deadline:
            pred = client.predictions.get(pred.id)
            out["status"] = pred.status
            if pred.status in {"succeeded", "failed", "canceled"}:
                out["error"] = str(pred.error) if pred.error else None
                out["logs"] = (pred.logs or "")[-2000:]
                if pred.status == "succeeded":
                    raw = pred.output
                    out["output"] = (
                        "".join(str(x) for x in raw)[:600]
                        if isinstance(raw, list)
                        else str(raw)[:600]
                    )
                break
            time.sleep(3)
        else:
            out["status"] = out.get("status", "timeout")
            out["error"] = out.get("error") or f"timeout after {wait_s}s"
    except Exception as exc:
        out["status"] = "exception"
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--wait", type=int, default=120)
    args = parser.parse_args()

    token = os.environ.get("REPLICATE_API_TOKEN", "").strip()
    if not token:
        print("REPLICATE_API_TOKEN не задан", file=sys.stderr)
        return 1

    client = replicate.Client(api_token=token)
    print(f"video: {SAMPLE_URL[:70]}…", flush=True)
    results = []
    for model in args.models:
        print(f"\n--- {model} ---", flush=True)
        r = probe(client, model, SAMPLE_URL, args.wait)
        results.append(r)
        print(f"  status: {r.get('status')}", flush=True)
        if r.get("prediction_id"):
            print(f"  id: {r['prediction_id']}", flush=True)
        if r.get("error"):
            print(f"  error: {str(r['error'])[:350]}", flush=True)
        if r.get("output"):
            print(f"  output: {r['output'][:300]}", flush=True)
        if r.get("logs"):
            tail = r["logs"].strip().splitlines()[-4:]
            print("  logs:", " | ".join(tail), flush=True)

    ok = sum(1 for r in results if r.get("status") == "succeeded")
    print(f"\n=== SUMMARY: {ok}/{len(results)} succeeded ===", flush=True)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
