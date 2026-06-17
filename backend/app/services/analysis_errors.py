"""Typed analysis errors and helpers for graceful (partial) delivery.

When the model refuses to analyze a piece of content (``block_reason``), we do
not fail the whole report. Instead we deliver everything that did analyze and
inject an explicit "review this fragment manually" finding for the part that did
not, so the editor always gets an openable report and knows what to re-check.
"""

from __future__ import annotations

from app.schemas.analysis import GeminiAnalysisResult, GeminiScene, GeminiSceneRisk

# Marker text used to recognise an auto-injected manual-review finding.
REVIEW_RISK = "Требует ручного просмотра"
REVIEW_RISK_LEVEL = "warning"


class ContentBlockedError(RuntimeError):
    """Raised when the model refuses to analyze the input (content block).

    This is a permanent, per-content outcome (not transient): retrying the same
    model rarely helps, so callers either fall back to another model or deliver
    a partial result with a manual-review marker.
    """

    def __init__(self, block_reason: object = None, message: str | None = None) -> None:
        self.block_reason = block_reason
        super().__init__(
            message
            or (
                f"Gemini blocked the input (block_reason={block_reason}). "
                "Контент отклонён моделью даже при отключённых фильтрах."
            )
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
    return GeminiScene(
        scene_number=scene_number,
        start_time=start,
        end_time=end,
        description=(
            f"Фрагмент {start}–{end} не удалось проанализировать автоматически "
            "(контент отклонён моделью)."
        ),
        risks=[
            GeminiSceneRisk(
                risk=REVIEW_RISK,
                risk_level=REVIEW_RISK_LEVEL,
                reason=(
                    reason
                    or "Модель отказалась анализировать этот фрагмент."
                ),
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
