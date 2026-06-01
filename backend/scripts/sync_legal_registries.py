#!/usr/bin/env python3
"""Download and normalize legal registries for offline compliance checks.

Sources:
- Foreign agents: community mirror of Minjust registry (fz255/foreign-agents).
- Extremist orgs: optional manual/CSV; extend when official export is wired.

Usage:
  python scripts/sync_legal_registries.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "app" / "data" / "registries"

FOREIGN_AGENTS_URL = (
    "https://raw.githubusercontent.com/fz255/foreign-agents/main/registry.json"
)


def sync_foreign_agents(client: httpx.Client) -> list[dict]:
    response = client.get(FOREIGN_AGENTS_URL, timeout=120)
    response.raise_for_status()
    raw = response.json()
    if not isinstance(raw, list):
        raise ValueError("Unexpected foreign agents payload")

    active = [row for row in raw if not (row.get("dateOut") or "").strip()]
    return active


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client(follow_redirects=True) as client:
        foreign_agents = sync_foreign_agents(client)

    fa_path = OUT_DIR / "foreign_agents.json"
    fa_path.write_text(
        json.dumps(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "source": FOREIGN_AGENTS_URL,
                "official": "https://minjust.gov.ru/ru/activity/directions/998/",
                "count": len(foreign_agents),
                "entries": foreign_agents,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    ext_path = OUT_DIR / "extremist_orgs.json"
    if not ext_path.exists():
        ext_path.write_text(
            json.dumps(
                {
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "source": "manual",
                    "official": "https://minjust.gov.ru/",
                    "count": 0,
                    "entries": [],
                    "note": "Run with --extremist-csv when export is available",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    meta = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "foreign_agents_source": "https://minjust.gov.ru/ru/activity/directions/998/",
        "foreign_agents_mirror": FOREIGN_AGENTS_URL,
        "extremist_orgs_source": "https://minjust.gov.ru/",
        "foreign_agents_count": len(foreign_agents),
        "extremist_orgs_count": json.loads(ext_path.read_text(encoding="utf-8")).get(
            "count", 0
        ),
    }
    (OUT_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"foreign_agents: {len(foreign_agents)} active -> {fa_path}")
    print(f"meta -> {OUT_DIR / 'meta.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
