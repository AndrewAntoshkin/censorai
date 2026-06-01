#!/usr/bin/env python3
"""Download and normalize legal registries for offline compliance checks.

Primary source: official Minjust registry API (reestrs.minjust.gov.ru).
Fallback: community mirror (fz255/foreign-agents) if the API is unavailable.

Usage:
  python scripts/sync_legal_registries.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "app" / "data" / "registries"

MINJUST_REGISTRY_PAGE = "https://minjust.gov.ru/ru/pages/reestr-inostryannykh-agentov/"
MINJUST_API_BASE = "https://reestrs.minjust.gov.ru"
FOREIGN_AGENTS_REGISTRY_ID = "39b95df9-9a68-6b6d-e1e3-e6388507067e"
FOREIGN_AGENTS_MIRROR = (
    "https://raw.githubusercontent.com/fz255/foreign-agents/main/registry.json"
)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CensorAI/1.0; +https://censorai.vercel.app)",
    "Content-Type": "application/json",
}


def _normalize_date(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    # API may return epoch ms in lastModified fields; date fields are YYYY-MM-DD.
    if re.fullmatch(r"\d{13}", text):
        return ""
    return text[:10]


def _row_from_minjust(value: dict) -> dict:
    return {
        "id": str(value.get("id") or value.get("field_1_i") or ""),
        "fullName": (value.get("field_2_s") or "").strip(),
        "law": (value.get("field_3_s") or "").strip(),
        "dateIn": _normalize_date(value.get("field_4_dt") or value.get("field_4_s")),
        "dateOut": _normalize_date(value.get("field_5_dt") or value.get("field_5_s")),
        "resources": (value.get("field_6_s") or "").strip(),
        "members": (value.get("field_13_s") or "").strip(),
        "address": (value.get("field_14_s") or "").strip(),
        "agentType": (value.get("field_7_s") or "").strip(),
    }


def sync_foreign_agents_minjust(client: httpx.Client) -> list[dict]:
    active: list[dict] = []
    offset = 0
    limit = 200
    total = None

    while True:
        response = client.post(
            f"{MINJUST_API_BASE}/rest/registry/{FOREIGN_AGENTS_REGISTRY_ID}/values",
            json={"offset": offset, "limit": limit, "search": ""},
            headers=_HEADERS,
            timeout=120,
        )
        response.raise_for_status()
        payload = response.json()
        if total is None:
            total = int(payload.get("size") or 0)

        batch = payload.get("values") or []
        if not batch:
            break

        for raw in batch:
            row = _row_from_minjust(raw)
            if not row["fullName"]:
                continue
            if row["dateOut"]:
                continue
            active.append(row)

        offset += len(batch)
        if offset >= total or len(batch) < limit:
            break

    return active


def sync_foreign_agents_mirror(client: httpx.Client) -> list[dict]:
    response = client.get(FOREIGN_AGENTS_MIRROR, timeout=120)
    response.raise_for_status()
    raw = response.json()
    if not isinstance(raw, list):
        raise ValueError("Unexpected foreign agents mirror payload")
    return [row for row in raw if not (row.get("dateOut") or "").strip()]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source = "minjust_api"
    official = MINJUST_REGISTRY_PAGE

    with httpx.Client(follow_redirects=True, timeout=120.0) as client:
        try:
            foreign_agents = sync_foreign_agents_minjust(client)
        except Exception as exc:
            print(f"Minjust API failed ({exc}), using mirror fallback…", file=sys.stderr)
            foreign_agents = sync_foreign_agents_mirror(client)
            source = FOREIGN_AGENTS_MIRROR
            official = "https://minjust.gov.ru/ru/activity/directions/998/"
            if len(foreign_agents) < 800:
                print(
                    "Warning: mirror has fewer entries than the official registry (~1200).",
                    file=sys.stderr,
                )

    fa_path = OUT_DIR / "foreign_agents.json"
    fa_path.write_text(
        json.dumps(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "source": source,
                "official": official,
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
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    meta = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "foreign_agents_source": official,
        "foreign_agents_api": MINJUST_API_BASE,
        "foreign_agents_registry_id": FOREIGN_AGENTS_REGISTRY_ID,
        "foreign_agents_mirror": FOREIGN_AGENTS_MIRROR,
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
    print(f"source: {source}")
    print(f"meta -> {OUT_DIR / 'meta.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
