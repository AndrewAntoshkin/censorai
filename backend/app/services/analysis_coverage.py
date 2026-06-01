"""Detect incomplete model output and build full-coverage analysis prompts."""

from __future__ import annotations

from app.schemas.analysis import GeminiAnalysisResult

# Replicate Gemini 3.5 Flash max; never send less — smaller values truncate long videos.
FULL_ANALYSIS_MAX_OUTPUT_TOKENS = 65535


def parse_timecode_seconds(value: str | None) -> int | None:
    if not value:
        return None
    parts = value.strip().split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(float(parts[1]))
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
    except ValueError:
        return None
    return None


def format_duration(seconds: float | int) -> str:
    total = int(round(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def estimate_duration_seconds(file_size_bytes: int) -> int | None:
    """Rough length from file size when client did not send duration (~45 KB/s)."""
    if file_size_bytes < 8 * 1024 * 1024:
        return None
    return int(file_size_bytes / 45_000)


def expected_duration_seconds(
    file_size_bytes: int,
    stored_duration: float | None,
) -> int | None:
    if stored_duration and stored_duration > 30:
        return int(stored_duration)
    return estimate_duration_seconds(file_size_bytes)


def max_scene_end_seconds(result: GeminiAnalysisResult) -> int:
    last = 0
    for scene in result.scenes:
        for key in (scene.end_time, scene.start_time):
            sec = parse_timecode_seconds(key)
            if sec is not None:
                last = max(last, sec)
    return last


def is_incomplete_coverage(
    file_size_bytes: int,
    result: GeminiAnalysisResult,
    *,
    expected_seconds: int | None = None,
) -> bool:
    title = (result.video_title or "").lower()
    if "фрагмент" in title:
        return True

    reported = parse_timecode_seconds(result.duration)
    last_end = max_scene_end_seconds(result)

    if expected_seconds and expected_seconds > 120:
        threshold = int(expected_seconds * 0.82)
        if reported is not None and reported < threshold:
            return True
        if last_end > 0 and last_end < threshold:
            return True

    size_mb = file_size_bytes / (1024 * 1024)
    if size_mb >= 20:
        min_expected = 8 * 60 if size_mb < 35 else 12 * 60
        if reported is not None and reported < min_expected:
            return True
        if last_end > 0 and last_end < min_expected:
            return True

    return False


def full_coverage_prompt_suffix(expected_seconds: int | None) -> str:
    if not expected_seconds or expected_seconds < 60:
        return (
            "\n\n## Обязательное требование\n"
            "Проанализируй видео от первого до последнего кадра. "
            "Поле duration — полная длительность файла. Не используй слово «фрагмент» в video_title."
        )
    label = format_duration(expected_seconds)
    return (
        f"\n\n## Обязательное требование\n"
        f"Длительность загруженного файла: {label} ({expected_seconds} сек). "
        f"Проанализируй ВЕСЬ ролик до {label} включительно. "
        f"Поле duration в JSON должно быть {label} или близко к этому. "
        f"Не помечай video_title как «фрагмент». "
        f"Таймкоды последних сцен должны доходить почти до конца ролика."
    )
