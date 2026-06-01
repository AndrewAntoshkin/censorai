#!/usr/bin/env python3
"""Run blob cleanup on production via API."""

from __future__ import annotations

import json
import sys

import httpx

DEFAULT_BASE = "https://censorai.vercel.app"
SECRET = "censor-demo-2026"


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    base = DEFAULT_BASE
    for arg in sys.argv[1:]:
        if arg.startswith("http"):
            base = arg.rstrip("/")

    with httpx.Client(base_url=base, timeout=300.0) as client:
        response = client.post(
            "/api/files/blob-cleanup",
            json={"secret": SECRET, "dry_run": dry_run},
        )
    print(response.status_code)
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except Exception:
        print(response.text[:2000])
    return 0 if response.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
