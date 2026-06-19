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
import ssl
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
# reestrs.minjust.gov.ru serves ONLY the leaf cert and omits the GlobalSign
# intermediate ("GCC R3 DV TLS CA 2020"). Python/httpx cannot chase the AIA URL
# like browsers/curl do, so verification fails with "unable to get local issuer
# certificate" even though the GlobalSign root is trusted. We embed the public
# intermediate (signed by GlobalSign Root R3, which certifi trusts) and add it
# to the trust store so the chain validates — still a fully verified TLS
# connection (no verify=False). Inlined (not a .pem file) so it ships with the
# code through .gitignore '*.pem' to CI and Vercel.
# Source: http://secure.globalsign.com/cacert/gsgccr3dvtlsca2020.crt
MINJUST_INTERMEDIATE_PEM_DATA = """\
-----BEGIN CERTIFICATE-----
MIIEsDCCA5igAwIBAgIQd70OB0LV2enQSdd00CpvmjANBgkqhkiG9w0BAQsFADBM
MSAwHgYDVQQLExdHbG9iYWxTaWduIFJvb3QgQ0EgLSBSMzETMBEGA1UEChMKR2xv
YmFsU2lnbjETMBEGA1UEAxMKR2xvYmFsU2lnbjAeFw0yMDA3MjgwMDAwMDBaFw0y
OTAzMTgwMDAwMDBaMFMxCzAJBgNVBAYTAkJFMRkwFwYDVQQKExBHbG9iYWxTaWdu
IG52LXNhMSkwJwYDVQQDEyBHbG9iYWxTaWduIEdDQyBSMyBEViBUTFMgQ0EgMjAy
MDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAKxnlJV/de+OpwyvCXAJ
IcxPCqkFPh1lttW2oljS3oUqPKq8qX6m7K0OVKaKG3GXi4CJ4fHVUgZYE6HRdjqj
hhnuHY6EBCBegcUFgPG0scB12Wi8BHm9zKjWxo3Y2bwhO8Fvr8R42pW0eINc6OTb
QXC0VWFCMVzpcqgz6X49KMZowAMFV6XqtItcG0cMS//9dOJs4oBlpuqX9INxMTGp
6EASAF9cnlAGy/RXkVS9nOLCCa7pCYV+WgDKLTF+OK2Vxw3RUJ/p8009lQeUARv2
UCcNNPCifYX1xIspvarkdjzLwzOdLahDdQbJON58zN4V+lMj0msg+c0KnywPIRp3
BMkCAwEAAaOCAYUwggGBMA4GA1UdDwEB/wQEAwIBhjAdBgNVHSUEFjAUBggrBgEF
BQcDAQYIKwYBBQUHAwIwEgYDVR0TAQH/BAgwBgEB/wIBADAdBgNVHQ4EFgQUDZjA
c3+rvb3ZR0tJrQpKDKw+x3wwHwYDVR0jBBgwFoAUj/BLf6guRSSuTVD6Y5qL3uLd
G7wwewYIKwYBBQUHAQEEbzBtMC4GCCsGAQUFBzABhiJodHRwOi8vb2NzcDIuZ2xv
YmFsc2lnbi5jb20vcm9vdHIzMDsGCCsGAQUFBzAChi9odHRwOi8vc2VjdXJlLmds
b2JhbHNpZ24uY29tL2NhY2VydC9yb290LXIzLmNydDA2BgNVHR8ELzAtMCugKaAn
hiVodHRwOi8vY3JsLmdsb2JhbHNpZ24uY29tL3Jvb3QtcjMuY3JsMEcGA1UdIARA
MD4wPAYEVR0gADA0MDIGCCsGAQUFBwIBFiZodHRwczovL3d3dy5nbG9iYWxzaWdu
LmNvbS9yZXBvc2l0b3J5LzANBgkqhkiG9w0BAQsFAAOCAQEAy8j/c550ea86oCkf
r2W+ptTCYe6iVzvo7H0V1vUEADJOWelTv07Obf+YkEatdN1Jg09ctgSNv2h+LMTk
KRZdAXmsE3N5ve+z1Oa9kuiu7284LjeS09zHJQB4DJJJkvtIbjL/ylMK1fbMHhAW
i0O194TWvH3XWZGXZ6ByxTUIv1+kAIql/Mt29PmKraTT5jrzcVzQ5A9jw16yysuR
XRrLODlkS1hyBjsfyTNZrmL1h117IFgntBA5SQNVl9ckedq5r4RSAU85jV8XK5UL
REjRZt2I6M9Po9QL7guFLu4sPFJpwR1sPJvubS2THeo7SxYoNDtdyBHs7euaGcMa
D/fayQ==
-----END CERTIFICATE-----
"""

# Minjust publishes the federal list of extremist organisations only as an HTML
# page on the (slow, SPA) main site — there is no grid-API registry for it (the
# 25 reestrs.minjust.gov.ru registries do not include it). So the extremist-org
# list is maintained as a curated bundled file (extremist_orgs.json) rather than
# synced; this URL is the public reference it is curated against.
EXTREMIST_ORGS_SOURCE = "https://www.consultant.ru/document/cons_doc_LAW_511970/"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CensorAI/1.0; +https://censorai.vercel.app)",
    "Content-Type": "application/json",
}


def _ssl_context() -> ssl.SSLContext:
    """certifi trust store plus the embedded Minjust GlobalSign intermediate."""
    try:
        import certifi

        ctx = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
    try:
        ctx.load_verify_locations(cadata=MINJUST_INTERMEDIATE_PEM_DATA)
    except Exception as exc:  # pragma: no cover - defensive
        print(
            f"Warning: could not load Minjust intermediate cert ({exc}).",
            file=sys.stderr,
        )
    return ctx


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

    with httpx.Client(
        follow_redirects=True, timeout=120.0, verify=_ssl_context()
    ) as client:
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

    # Extremist organisations have no machine-readable feed, so the list is a
    # curated bundled file. Never clobber it here — only create an empty stub if
    # it is missing entirely.
    ext_path = OUT_DIR / "extremist_orgs.json"
    if not ext_path.exists():
        ext_path.write_text(
            json.dumps(
                {
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "source": "curated",
                    "official": EXTREMIST_ORGS_SOURCE,
                    "count": 0,
                    "entries": [],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    ext_data = json.loads(ext_path.read_text(encoding="utf-8"))
    ext_count = ext_data.get("count")
    if ext_count is None:
        ext_count = len(ext_data.get("entries", []))

    meta = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "foreign_agents_source": official,
        "foreign_agents_api": MINJUST_API_BASE,
        "foreign_agents_registry_id": FOREIGN_AGENTS_REGISTRY_ID,
        "foreign_agents_mirror": FOREIGN_AGENTS_MIRROR,
        "extremist_orgs_source": ext_data.get("official", EXTREMIST_ORGS_SOURCE),
        "foreign_agents_count": len(foreign_agents),
        "extremist_orgs_count": ext_count,
    }
    (OUT_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"foreign_agents: {len(foreign_agents)} active -> {fa_path}")
    print(f"extremist_orgs: {ext_count} curated -> {ext_path}")
    print(f"source: {source}")
    print(f"meta -> {OUT_DIR / 'meta.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
