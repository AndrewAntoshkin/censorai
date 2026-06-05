"""Split long videos for Replicate (max 45 min per clip) via ffmpeg."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import httpx

from app.core.config import settings
from app.services.analysis_coverage import format_duration
from app.services.media_ffmpeg import ffmpeg_binary, ffprobe_binary

logger = logging.getLogger(__name__)

MAX_SEGMENT_SECONDS = settings.REPLICATE_MAX_VIDEO_MINUTES * 60
MIN_TAIL_SECONDS = 3 * 60
SHORT_OVERFLOW_FIRST_SECONDS = 40 * 60


def needs_segmentation(total_seconds: int) -> bool:
    return total_seconds > MAX_SEGMENT_SECONDS


def plan_segment_ranges(total_seconds: int) -> list[tuple[int, int]]:
    """Return (start_sec, duration_sec) slices for the full file.

    Rules (demo / Replicate):
    - <= 45 min: one segment.
    - 45 min < total <= 48 min: 40 min + remainder (target ~8 min).
    - Otherwise: 45 min chunks; if the tail after a 45 min head would be < 3 min,
      use 40 + remainder from that position instead of 45 + tiny tail.
    """
    if total_seconds <= 0:
        return [(0, 0)]

    if total_seconds <= MAX_SEGMENT_SECONDS:
        return [(0, total_seconds)]

    if total_seconds <= MAX_SEGMENT_SECONDS + MIN_TAIL_SECONDS:
        first = SHORT_OVERFLOW_FIRST_SECONDS
        return [(0, first), (first, total_seconds - first)]

    segments: list[tuple[int, int]] = []
    pos = 0
    while True:
        remaining = total_seconds - pos
        if remaining <= MAX_SEGMENT_SECONDS:
            if remaining > 0:
                segments.append((pos, remaining))
            break

        next_remaining = remaining - MAX_SEGMENT_SECONDS
        if 0 < next_remaining < MIN_TAIL_SECONDS:
            first = SHORT_OVERFLOW_FIRST_SECONDS
            segments.append((pos, first))
            segments.append((pos + first, total_seconds - pos - first))
            break

        segments.append((pos, MAX_SEGMENT_SECONDS))
        pos += MAX_SEGMENT_SECONDS

    return segments


def probe_duration_seconds(
    storage_path: str, *, file_id: str | None = None
) -> int | None:
    """Duration via ffprobe; None if unavailable."""
    if storage_path.startswith("chunk-session:"):
        if file_id:
            from app.services.replicate_media import build_replicate_media_url

            storage_path = build_replicate_media_url(file_id)
        else:
            return None

    if storage_path.startswith("s3://"):
        from app.services.object_storage import presigned_get_url

        storage_path = presigned_get_url(storage_path)

    if storage_path.startswith(("http://", "https://")):
        probed = _ffprobe_duration(storage_path)
        if probed:
            return probed
    local, temps = _resolve_local_paths(storage_path)
    if not local:
        _cleanup_temps(temps)
        return None
    try:
        return _ffprobe_duration(local)
    finally:
        _cleanup_temps(temps)


def _segment_source(storage_path: str, *, file_id: str | None = None) -> tuple[str, list[Path]]:
    """Return ffmpeg input path; download to temp only for non-HTTP local paths."""
    if storage_path.startswith("chunk-session:"):
        if not file_id:
            raise RuntimeError("file_id required to segment chunk-session video")
        from app.services.replicate_media import build_replicate_media_url

        return build_replicate_media_url(file_id), []

    if storage_path.startswith(("http://", "https://")):
        return storage_path, []

    if storage_path.startswith("s3://"):
        from app.services.object_storage import presigned_get_url

        return presigned_get_url(storage_path), []

    source, temps = _resolve_local_paths(storage_path)
    if not source:
        raise FileNotFoundError("Не удалось получить локальный файл для нарезки")
    return source, temps


def prepare_single_segment_file(
    storage_path: str,
    start_sec: int,
    duration_sec: int,
    *,
    index: int = 0,
    file_id: str | None = None,
) -> tuple[str, list[Path]]:
    """Cut one range. Caller must delete returned temp paths after upload."""
    if not ffmpeg_binary():
        raise RuntimeError(
            "ffmpeg не установлен на сервере. Для роликов длиннее "
            f"{settings.REPLICATE_MAX_VIDEO_MINUTES} мин нужна нарезка через ffmpeg."
        )

    source, source_temps = _segment_source(storage_path, file_id=file_id)
    out = Path(tempfile.mkstemp(suffix=f"_seg{index}.mp4")[1])
    try:
        _ffmpeg_segment(source, start_sec, duration_sec, out)
        return str(out), source_temps + [out]
    except Exception:
        out.unlink(missing_ok=True)
        _cleanup_temps(source_temps)
        raise


def prepare_segment_files(
    storage_path: str,
    ranges: list[tuple[int, int]],
) -> tuple[list[str], list[Path]]:
    """Cut all ranges (tests/local). Prefer one-at-a-time on serverless."""
    segment_paths: list[str] = []
    all_temps: list[Path] = []
    for index, (start_sec, duration_sec) in enumerate(ranges):
        path, temps = prepare_single_segment_file(
            storage_path, start_sec, duration_sec, index=index
        )
        segment_paths.append(path)
        all_temps.extend(temps)
    return segment_paths, all_temps


def segment_prompt_suffix(
    index: int,
    total: int,
    start_sec: int,
    duration_sec: int,
) -> str:
    return (
        f"\n\n## Часть {index + 1} из {total}\n"
        f"Фрагмент полного ролика: с {format_duration(start_sec)}, "
        f"длительность {format_duration(duration_sec)}. "
        f"Таймкоды в JSON — относительно начала этого фрагмента (0:00). "
        f"Не используй слово «фрагмент» в video_title."
    )


def _resolve_local_paths(storage_path: str) -> tuple[str, list[Path]]:
    temps: list[Path] = []
    if not storage_path:
        return "", temps

    if storage_path.startswith("s3://"):
        from app.services.object_storage import download_object_to_tempfile

        temp = download_object_to_tempfile(storage_path)
        temps.append(temp)
        return str(temp), temps

    if storage_path.startswith(("http://", "https://")):
        suffix = ".mp4"
        if "." in storage_path.split("?")[0].rsplit("/", 1)[-1]:
            suffix = "." + storage_path.split("?")[0].rsplit(".", 1)[-1].lower()[:8]
        temp = Path(tempfile.mkstemp(suffix=suffix)[1])
        with httpx.Client(timeout=600, follow_redirects=True) as client:
            response = client.get(storage_path)
        response.raise_for_status()
        temp.write_bytes(response.content)
        temps.append(temp)
        return str(temp), temps

    path = Path(storage_path)
    if path.is_file():
        return str(path), temps

    return "", temps


def _ffprobe_duration(path: str) -> int | None:
    probe = ffprobe_binary()
    if probe:
        cmd = [
            probe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
            if proc.returncode == 0:
                try:
                    return max(1, int(float((proc.stdout or "").strip())))
                except ValueError:
                    pass
            else:
                logger.warning(
                    "ffprobe exit %s: %s", proc.returncode, (proc.stderr or "")[:400]
                )
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("ffprobe failed: %s", exc)
    return _ffmpeg_probe_duration(path)


def _ffmpeg_probe_duration(path: str) -> int | None:
    ffmpeg = ffmpeg_binary()
    if not ffmpeg:
        logger.warning("ffprobe/ffmpeg not found — cannot probe duration")
        return None
    cmd = [ffmpeg, "-hide_banner", "-i", path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("ffmpeg probe failed: %s", exc)
        return None
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr or "")
    if not match:
        return None
    h, m, s = match.groups()
    return max(1, int(float(h) * 3600 + float(m) * 60 + float(s)))


def _ffmpeg_segment(source: str, start_sec: int, duration_sec: int, output: Path) -> None:
    ffmpeg = ffmpeg_binary()
    if not ffmpeg:
        raise RuntimeError("ffmpeg not available")
    # Keep only the first video + audio stream (drop subtitle/data streams that
    # break Gemini), stream-copy, and move moov to the front (+faststart) so the
    # model can read the segment. -ss before -i = fast keyframe seek.
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        str(start_sec),
        "-i",
        source,
        "-t",
        str(duration_sec),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c",
        "copy",
        "-avoid_negative_ts",
        "make_zero",
        "-movflags",
        "+faststart",
        str(output),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, check=False)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("ffmpeg timeout while cutting segment") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "")[:500]
        if "No space left on device" in detail or proc.returncode == -28:
            raise RuntimeError(
                f"ffmpeg segment failed (start={start_sec}s, dur={duration_sec}s): "
                "недостаточно места в /tmp на сервере (лимит Vercel ~512 МБ). "
                "Повторите загрузку или обработайте на машине с большим диском."
            )
        raise RuntimeError(
            f"ffmpeg segment failed (start={start_sec}s, dur={duration_sec}s): {detail}"
        )
    if not output.is_file() or output.stat().st_size < 1024:
        raise RuntimeError(f"ffmpeg produced empty segment: {output}")


def _cleanup_temps(paths: list[Path]) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Failed to remove temp %s: %s", path, exc)
