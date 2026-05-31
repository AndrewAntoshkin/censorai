#!/usr/bin/env python3
"""
Запуск golden-set eval против текущего промпта/парсера.

Использование:
    cd backend
    python -m eval.run_golden_set                    # только кейсы с video_path
    python -m eval.run_golden_set --dry-run          # показать кейсы без API
    python -m eval.run_golden_set --case age-rating-alcohol-16plus
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.schemas.analysis import GeminiAnalysisResult
from app.services.gemini_service import GeminiService

GOLDEN_SET_PATH = Path(__file__).resolve().parent / "golden_set.json"

AGE_ORDER = {"0+": 0, "6+": 1, "12+": 2, "16+": 3, "18+": 4}


def load_golden_set() -> dict:
    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        return json.load(f)


def collect_risk_slugs(result: GeminiAnalysisResult) -> set[str]:
    slugs: set[str] = set()
    for scene in result.scenes:
        for risk in scene.risks:
            if risk.risk:
                slugs.add(risk.risk)
    return slugs


def count_critical(result: GeminiAnalysisResult) -> int:
    count = 0
    for scene in result.scenes:
        for risk in scene.risks:
            if risk.risk_level == "critical":
                count += 1
    return count


def check_case(case: dict, result: GeminiAnalysisResult) -> list[str]:
    expect = case.get("expect", {})
    errors: list[str] = []
    found = collect_risk_slugs(result)

    for slug in expect.get("required_risks", []):
        if slug not in found:
            errors.append(f"missing required risk: {slug}")

    for slug in expect.get("forbidden_risks", []):
        if slug in found:
            errors.append(f"unexpected risk: {slug}")

    min_rating = expect.get("recommended_age_rating_min")
    if min_rating and result.recommended_age_rating:
        actual = AGE_ORDER.get(result.recommended_age_rating, -1)
        needed = AGE_ORDER.get(min_rating, 99)
        if actual < needed:
            errors.append(
                f"age rating too low: got {result.recommended_age_rating}, need >= {min_rating}"
            )
    elif min_rating and not result.recommended_age_rating:
        errors.append(f"missing recommended_age_rating (expected >= {min_rating})")

    min_triggers = expect.get("min_age_rating_triggers", 0)
    if len(result.age_rating_triggers) < min_triggers:
        errors.append(
            f"too few age_rating_triggers: {len(result.age_rating_triggers)} < {min_triggers}"
        )

    min_entities = expect.get("min_entities", 0)
    if len(result.entities) < min_entities:
        errors.append(f"too few entities: {len(result.entities)} < {min_entities}")

    max_critical = expect.get("max_critical_count")
    if max_critical is not None:
        critical = count_critical(result)
        if critical > max_critical:
            errors.append(f"too many critical risks: {critical} > {max_critical}")

    return errors


async def run_case(case: dict, service: GeminiService) -> tuple[bool, list[str]]:
    video_path = case.get("video_path")
    if not video_path:
        return False, ["skipped: video_path not set"]

    path = Path(video_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        return False, [f"skipped: file not found: {video_path}"]

    result = await service.analyze_video(str(path))
    errors = check_case(case, result)
    return len(errors) == 0, errors


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run golden-set eval")
    parser.add_argument("--dry-run", action="store_true", help="List cases without calling API")
    parser.add_argument("--case", help="Run single case by id")
    args = parser.parse_args()

    data = load_golden_set()
    cases = data["cases"]
    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            print(f"Case not found: {args.case}")
            return 1

    if args.dry_run:
        for case in cases:
            status = "ready" if case.get("video_path") else "needs video_path"
            print(f"[{status}] {case['id']}: {case['description']}")
        ready = sum(1 for c in cases if c.get("video_path"))
        print(f"\n{ready}/{len(cases)} cases ready to run")
        return 0

    service = GeminiService()
    passed = 0
    failed = 0
    skipped = 0

    for case in cases:
        ok, errors = await run_case(case, service)
        if errors and errors[0].startswith("skipped"):
            skipped += 1
            print(f"SKIP  {case['id']}: {errors[0]}")
        elif ok:
            passed += 1
            print(f"PASS  {case['id']}")
        else:
            failed += 1
            print(f"FAIL  {case['id']}:")
            for err in errors:
                print(f"       - {err}")

    runnable = passed + failed
    print(f"\nResults: {passed} passed, {failed} failed, {skipped} skipped ({runnable} runnable)")
    if runnable:
        print(f"Pass rate: {passed / runnable * 100:.0f}%")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
