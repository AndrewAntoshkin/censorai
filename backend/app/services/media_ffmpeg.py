"""Resolve ffmpeg/ffprobe binaries (system PATH or imageio-ffmpeg wheel on Vercel)."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

_cached_ffmpeg: str | None = None
_cached_ffprobe: str | None = None


def ffmpeg_binary() -> str | None:
    global _cached_ffmpeg
    if _cached_ffmpeg is not None:
        return _cached_ffmpeg or None
    found = shutil.which("ffmpeg")
    if found:
        _cached_ffmpeg = found
        return found
    try:
        import imageio_ffmpeg

        _cached_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        logger.info("Using bundled ffmpeg: %s", _cached_ffmpeg)
        return _cached_ffmpeg
    except Exception as exc:
        logger.warning("Bundled ffmpeg unavailable: %s", exc)
        _cached_ffmpeg = ""
        return None


def ffprobe_binary() -> str | None:
    global _cached_ffprobe
    if _cached_ffprobe is not None:
        return _cached_ffprobe or None
    found = shutil.which("ffprobe")
    if found:
        _cached_ffprobe = found
        return found
    ff = ffmpeg_binary()
    if ff:
        probe = Path(ff).parent / "ffprobe"
        if probe.is_file():
            _cached_ffprobe = str(probe)
            return _cached_ffprobe
    _cached_ffprobe = ""
    return None
