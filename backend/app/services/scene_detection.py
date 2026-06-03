"""Lightweight scene-change detection via ffmpeg (stage 4 pre-pass)."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_SCENE_RE = re.compile(r"pts_time:([0-9.]+)")


def detect_scene_timestamps(
    video_path: str,
    *,
    threshold: float = 0.32,
    max_scenes: int = 120,
) -> list[float]:
    """Return seconds where scene changes are likely. Empty if ffmpeg unavailable."""
    if video_path.startswith(("http://", "https://")):
        return []

    path = Path(video_path)
    if not path.exists():
        return []

    if not shutil.which("ffmpeg"):
        logger.warning("ffmpeg not found — scene pre-pass skipped")
        return []

    filter_expr = f"select='gt(scene,{threshold})',showinfo"
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "info",
        "-i",
        str(path),
        "-vf",
        filter_expr,
        "-an",
        "-f",
        "null",
        "-",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("Scene detection failed: %s", exc)
        return []

    text = (proc.stderr or "") + (proc.stdout or "")
    times: list[float] = []
    for match in _SCENE_RE.finditer(text):
        try:
            t = float(match.group(1))
        except ValueError:
            continue
        if not times or t - times[-1] > 1.0:
            times.append(t)
        if len(times) >= max_scenes:
            break
    return times


def scene_hints_for_prompt(timestamps: list[float]) -> str:
    if not timestamps:
        return ""
    sample = timestamps[:40]
    formatted = ", ".join(f"{t:.1f}s" for t in sample)
    extra = f" (и ещё {len(timestamps) - len(sample)})" if len(timestamps) > len(sample) else ""
    return (
        "\n\nДополнительно: автоматический предпросмотр отметил смены планов на "
        f"{formatted}{extra}. Удели этим моментам повышенное внимание при оценке рисков."
    )
