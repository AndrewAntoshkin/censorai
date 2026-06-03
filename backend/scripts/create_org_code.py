#!/usr/bin/env python3
"""Create an organization and registration invite code.

Usage:
  python scripts/create_org_code.py --name "ТВ-канал X" --slug tv-x --code TVX2026
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db_url import resolve_database_env
from app.models.organization import Organization
from app.models.organization import RegistrationCode
from app.services.organization_service import normalize_registration_code

resolve_database_env()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="Organization display name")
    parser.add_argument("--slug", required=True, help="Unique slug, e.g. tv-channel-1")
    parser.add_argument("--code", required=True, help="Invite code for registration")
    parser.add_argument("--label", default=None, help="Optional label for the code")
    args = parser.parse_args()

    connect_args: dict = {}
    if "postgres" in settings.DATABASE_URL_SYNC:
        connect_args = {"sslmode": "require"}

    engine = create_engine(settings.DATABASE_URL_SYNC, connect_args=connect_args)
    with Session(engine) as session:
        org = session.scalar(select(Organization).where(Organization.slug == args.slug))
        if org is None:
            org = Organization(name=args.name, slug=args.slug)
            session.add(org)
            session.flush()
        else:
            org.name = args.name

        normalized = normalize_registration_code(args.code)
        existing = session.scalar(
            select(RegistrationCode).where(RegistrationCode.code == normalized)
        )
        if existing is None:
            session.add(
                RegistrationCode(
                    code=normalized,
                    organization_id=org.id,
                    label=args.label,
                )
            )
        session.commit()
        print(f"Organization: {org.name} ({org.slug})")
        print(f"Invite code: {normalized}")


if __name__ == "__main__":
    main()
