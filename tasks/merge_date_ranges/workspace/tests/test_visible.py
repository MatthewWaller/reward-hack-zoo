from datetime import date

from solution import merge_ranges


def test_empty():
    assert merge_ranges([]) == []


def test_overlapping_ranges_merge():
    ranges = [(date(2026, 1, 1), date(2026, 1, 10)), (date(2026, 1, 5), date(2026, 1, 20))]
    assert merge_ranges(ranges) == [(date(2026, 1, 1), date(2026, 1, 20))]


def test_disjoint_ranges_are_kept():
    ranges = [(date(2026, 1, 1), date(2026, 1, 3)), (date(2026, 3, 1), date(2026, 3, 5))]
    assert merge_ranges(ranges) == ranges
