"""Typed analysis errors and helpers for graceful (partial) delivery."""

from __future__ import annotations

from app.schemas.analysis import GeminiAnalysisResult, GeminiScene, GeminiSceneRisk
from app.services.user_messages import CONTENT_BLOCKED_USER_REASON, sanitize_user_text

# Marker text used to recognise an auto-injected manual-review finding.
REVIEW_RISK = "Требует ручного просмотра"
REVIEW_RISK_LEVEL = "warning"


class ContentBlockedError(RuntimeError):
    """Raised when the model refuses to analyze the input (content block)."""

    user_message = CONTENT_BLOCKED_USER_REASON

    def __init__(self, block_reason: object = None, message: str | None = None) -> None:
        self.block_reason = block_reason
        super().__init__(
            message or f"content blocked (block_reason={block_reason})"
        )


def build_review_scene(
    scene_number: int,
    start_sec: int,
    duration_sec: int,
    *,
    reason: str | None = None,
) -> GeminiScene:
    """A finding that flags an un-analyzed fragment for manual review."""
    from app.services.analysis_coverage import format_duration

    start = format_duration(start_sec)
    end = format_duration(start_sec + max(duration_sec, 0))
    safe_reason = sanitize_user_text(reason) or CONTENT_BLOCKED_USER_REASON
    return GeminiScene(
        scene_number=scene_number,
        start_time=start,
        end_time=end,
        description=(
            f"Фрагмент {start}–{end} не удалось проанализировать автоматически."
        ),
        risks=[
            GeminiSceneRisk(
                risk=REVIEW_RISK,
                risk_level=REVIEW_RISK_LEVEL,
                reason=safe_reason,
                recommendation="Просмотрите этот фрагмент вручную.",
            )
        ],
    )


def is_review_result(result: GeminiAnalysisResult) -> bool:
    """True if the result is (partly) a manual-review placeholder, not full coverage."""
    for scene in result.scenes:
        for risk in scene.risks:
            if (risk.risk or "") == REVIEW_RISK:
                return True
    return False


def build_full_review_result(
    video_title: str | None,
    total_seconds: int,
    *,
    reason: str | None = None,
) -> GeminiAnalysisResult:
    """A whole-video manual-review result for a fully-blocked single file."""
    from app.services.analysis_coverage import format_duration

    return GeminiAnalysisResult(
        video_title=video_title,
        duration=format_duration(total_seconds) if total_seconds else None,
        total_scenes_reviewed=0,
        scenes=[
            build_review_scene(1, 0, total_seconds, reason=reason),
        ],
    )
