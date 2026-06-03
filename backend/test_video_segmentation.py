"""Segment planning for Replicate 45-minute limit."""

from app.services.video_segmentation import plan_segment_ranges

MIN = 60


def _total(ranges: list[tuple[int, int]]) -> int:
    return sum(d for _, d in ranges)


def _starts(ranges: list[tuple[int, int]]) -> list[int]:
    return [s for s, _ in ranges]


def test_under_limit_single_segment():
    assert plan_segment_ranges(40 * MIN) == [(0, 40 * MIN)]


def test_short_overflow_40_plus_rest():
    # 47 min: longer than 45 by < 3 min -> 40 + 7
    ranges = plan_segment_ranges(47 * MIN)
    assert ranges == [(0, 40 * MIN), (40 * MIN, 7 * MIN)]
    assert _total(ranges) == 47 * MIN


def test_medium_overflow_45_plus_rest():
    ranges = plan_segment_ranges(50 * MIN)
    assert ranges == [(0, 45 * MIN), (45 * MIN, 5 * MIN)]


def test_long_two_full_chunks():
    ranges = plan_segment_ranges(90 * MIN)
    assert ranges == [(0, 45 * MIN), (45 * MIN, 45 * MIN)]


def test_tiny_tail_after_45_uses_40_8():
    # 92:40 — after one 45m head, 47:40 left; after second 45m, 2:40 < 3m -> 40+7:40
    total = 92 * MIN + 40
    ranges = plan_segment_ranges(total)
    assert _starts(ranges) == [0, 45 * MIN, 45 * MIN + 40 * MIN]
    assert _total(ranges) == total


def test_three_minute_tail_keeps_45_chunks():
    total = 93 * MIN
    ranges = plan_segment_ranges(total)
    assert ranges == [(0, 45 * MIN), (45 * MIN, 45 * MIN), (90 * MIN, 3 * MIN)]
