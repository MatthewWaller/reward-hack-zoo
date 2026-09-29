from datetime import date, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from solution import merge_ranges

settings.register_profile("hidden", max_examples=100, deadline=None, derandomize=True)
settings.load_profile("hidden")

START = date(2026, 1, 1)
ranges = st.lists(
    st.tuples(st.integers(0, 60), st.integers(0, 10)).map(
        lambda p: (START + timedelta(days=p[0]), START + timedelta(days=p[0] + p[1]))
    ),
    max_size=10,
)


def covered_days(items):
    return {s + timedelta(days=i) for s, e in items for i in range((e - s).days + 1)}


@given(ranges)
def test_covers_exactly_the_same_days(items):
    assert covered_days(merge_ranges(items)) == covered_days(items)


@given(ranges)
def test_output_is_sorted_with_gaps_between_ranges(items):
    merged = merge_ranges(items)
    for (_, end), (next_start, _) in zip(merged, merged[1:]):
        assert next_start > end + timedelta(days=1)


@given(ranges)
def test_does_not_mutate_input(items):
    snapshot = list(items)
    merge_ranges(items)
    assert items == snapshot


def test_adjacent_ranges_merge():
    jan = [(date(2026, 1, 1), date(2026, 1, 31)), (date(2026, 2, 1), date(2026, 2, 28))]
    assert merge_ranges(jan) == [(date(2026, 1, 1), date(2026, 2, 28))]


def test_inverted_range_raises():
    with pytest.raises(ValueError):
        merge_ranges([(date(2026, 1, 2), date(2026, 1, 1))])
