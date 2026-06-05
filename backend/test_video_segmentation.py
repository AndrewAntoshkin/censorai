"""Segment planning for the Replicate/Gemini per-clip duration limit.

Tests reference the module constants so they stay correct if the limit changes.
"""

from app.services.video_segmentation import (
    MAX_SEGMENT_SECONDS as M,
    MIN_TAIL_SECONDS as TAIL,
    SHORT_OVERFLOW_FIRST_SECONDS as F,
    plan_segment_ranges,
)


def _total(ranges: list[tuple[int, int]]) -> int:
    return sum(d for _, d in ranges)


def test_under_limit_single_segment():
    assert plan_segment_ranges(M - 60) == [(0, M - 60)]


def test_at_limit_single_segment():
    assert plan_segment_ranges(M) == [(0, M)]


def test_tiny_overflow_uses_short_head_plus_rest():
    total = M + TAIL - 60  # just over M, tail would be < MIN_TAIL
    ranges = plan_segment_ranges(total)
    assert ranges == [(0, F), (F, total - F)]
    assert _total(ranges) == total


def test_medium_overflow_full_head_plus_rest():
    total = M + 10 * 60  # comfortably over M+TAIL
    ranges = plan_segment_ranges(total)
    assert ranges == [(0, M), (M, total - M)]
    assert _total(ranges) == total


def test_two_full_chunks():
    assert plan_segment_ranges(2 * M) == [(0, M), (M, M)]


def test_tiny_tail_in_loop_stays_under_limit():
    total = 2 * M + (TAIL - 60)  # second tail would be tiny -> short-head split
    ranges = plan_segment_ranges(total)
    assert _total(ranges) == total
    assert all(0 < d <= M for _, d in ranges)


def test_min_tail_keeps_full_chunks():
    total = 2 * M + TAIL
    ranges = plan_segment_ranges(total)
    assert ranges == [(0, M), (M, M), (2 * M, TAIL)]
    assert _total(ranges) == total
