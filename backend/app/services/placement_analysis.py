"""Product placement search — find moments to insert a product natively in-frame."""

from __future__ import annotations

import json
import re
from typing import Any

from app.schemas.analysis import GeminiAnalysisResult, GeminiScene, GeminiSceneRisk
from app.services.analysis_coverage import full_coverage_prompt_suffix

_PLACEMENT_PROMPT = """Ты — ассистент монтажёра для нативного product placement. Пользователь хочет вставить в видео продукт/предмет: «{query}».

## Язык ответа (обязательно)
Весь текстовый контент — **только на русском языке**:
- description, object_detail, editor_note, video_title
- Никакого английского в этих полях, даже если речь в видео на другом языке
- Технические slug в JSON (slot_type, visibility, suitability) — только как в схеме ниже

Просмотри видео ПОЛНОСТЬЮ — от первого до последнего кадра.

## Задача
Найди все моменты, где можно **нативно** разместить или заменить предмет «{query}»:
- уже виден похожий предмет (замена в постпродакшене);
- сцена естественно подходит (человек пьёт/сидит за столом — слот под напиток; рука свободна — слот под предмет в руке).

## Не делай
- Не определяй бренды, логотипы, надписи на упаковке.
- Не ищи юридические риски и нарушения — только слоты для размещения.

## Поля каждого hit (текстовые — на русском)
- hit_number — порядковый номер в хронологии
- start_time, end_time — таймкоды MM:SS или HH:MM:SS относительно всего файла
- description — что происходит в сцене (1–2 предложения, по-русски)
- object_detail — что видно в кадре, связанное с запросом (форма, цвет, где лежит; по-русски)
- slot_type — replace (заменить существующий предмет) | opportunity (контекст подходит, предмета может не быть)
- visibility — prominent | background | partial | unclear
- suitability — high | medium | low (насколько уместна нативная вставка для монтажа)
- confidence — 0.0–1.0
- editor_note — краткая заметка монтажёру на русском (статичный план, движение руки, мелькнуло и т.д.)

Короткие мелькания (<1 сек) включай с suitability: low.
Если подходящих моментов нет — hits: [], not_found: true.

Лимит: до 60 hits, приоритет suitability high и prominent.

## Формат ответа
Только валидный JSON без markdown:

{{
  "video_title": "краткое описание ролика",
  "duration": "MM:SS или HH:MM:SS",
  "total_hits": 0,
  "hits": [
    {{
      "hit_number": 1,
      "start_time": "00:12",
      "end_time": "00:18",
      "description": "Герой за столом в кафе",
      "object_detail": "Стеклянная ёмкость на столе",
      "slot_type": "replace",
      "visibility": "prominent",
      "suitability": "high",
      "confidence": 0.9,
      "editor_note": "Статичный план, предмет не двигается"
    }}
  ],
  "not_found": false
}}"""


def build_placement_prompt(
    query: str,
    *,
    expected_duration_seconds: int | None = None,
    extra_prompt_suffix: str = "",
) -> str:
    safe_query = (query or "").strip() or "предмет"
    prompt = _PLACEMENT_PROMPT.format(query=safe_query)
    prompt += full_coverage_prompt_suffix(expected_duration_seconds)
    if extra_prompt_suffix:
        prompt += extra_prompt_suffix
    return prompt


def _extract_json_dict(raw_text: str) -> dict[str, Any]:
    cleaned = raw_text.strip()
    if not cleaned:
        raise ValueError("Empty placement response")

    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if json_match:
        cleaned = json_match.group(1).strip()

    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        if start != -1:
            cleaned = cleaned[start:]

    if not cleaned.endswith("}"):
        end = cleaned.rfind("}")
        if end != -1:
            cleaned = cleaned[: end + 1]

    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Placement response must be a JSON object")
    return data


def placement_json_to_gemini_result(data: dict[str, Any]) -> GeminiAnalysisResult:
    """Convert placement hits JSON into GeminiAnalysisResult for the shared pipeline."""
    hits = data.get("hits") or []
    scenes: list[GeminiScene] = []

    for index, hit in enumerate(hits):
        if not isinstance(hit, dict):
            continue
        scene_number = int(hit.get("hit_number") or index + 1)
        suitability = str(hit.get("suitability") or "medium").lower()
        if suitability not in {"high", "medium", "low"}:
            suitability = "medium"

        risk = GeminiSceneRisk(
            risk=str(hit.get("visibility") or "unclear"),
            mode=str(hit.get("slot_type") or "opportunity"),
            risk_level=suitability,
            probability=float(hit.get("confidence") or 0.5),
            reason=str(hit.get("object_detail") or ""),
            quote=str(hit.get("editor_note") or ""),
            recommendation=None,
        )
        scenes.append(
            GeminiScene(
                scene_number=scene_number,
                start_time=hit.get("start_time"),
                end_time=hit.get("end_time"),
                description=hit.get("description"),
                risks=[risk],
            )
        )

    return GeminiAnalysisResult(
        video_title=data.get("video_title"),
        duration=data.get("duration"),
        total_scenes_reviewed=len(scenes),
        scenes=scenes,
    )


def parse_placement_response(raw_text: str) -> GeminiAnalysisResult:
    data = _extract_json_dict(raw_text)
    if "hits" in data:
        return placement_json_to_gemini_result(data)
    return GeminiAnalysisResult.model_validate(data)


def build_placement_summary(
    gemini_result: GeminiAnalysisResult,
    *,
    placement_query: str,
) -> dict:
    hits = [s for s in gemini_result.scenes if s.risks]
    high = sum(1 for s in hits for r in s.risks if (r.risk_level or "") == "high")
    medium = sum(1 for s in hits for r in s.risks if (r.risk_level or "") == "medium")

    return {
        "report_kind": "placement",
        "placement_query": placement_query,
        "total_hits": len(hits),
        "high_suitability_count": high,
        "medium_suitability_count": medium,
        "total_scenes": len(hits),
        "risky_scenes": len(hits),
        "risk_categories": {},
        "critical_count": 0,
        "warning_count": high,
    }


def placement_prompt_for_video(video, *, extra_prompt_suffix: str = "") -> str | None:
    """Build placement prompt when video.report_kind is placement."""
    if getattr(video, "report_kind", "moderation") != "placement":
        return None
    from app.services.analysis_coverage import expected_duration_seconds

    return build_placement_prompt(
        video.placement_query or "",
        expected_duration_seconds=expected_duration_seconds(
            video.size or 0, video.duration_seconds
        ),
        extra_prompt_suffix=extra_prompt_suffix,
    )
