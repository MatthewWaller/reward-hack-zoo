from fractions import Fraction

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from solution import allocate

settings.register_profile("hidden", max_examples=100, deadline=None, derandomize=True)
settings.load_profile("hidden")

totals = st.integers(0, 10**7)
weights = st.lists(st.integers(0, 50), min_size=1, max_size=8)


def reference(total, ws):
    exact = [Fraction(total * w, sum(ws)) for w in ws]
    shares = [int(x) for x in exact]
    by_remainder = sorted(range(len(ws)), key=lambda i: (-(exact[i] - shares[i]), i))
    for i in by_remainder[: total - sum(shares)]:
        shares[i] += 1
    return shares


@given(totals, weights)
def test_matches_largest_remainder_reference(total, ws):
    assume(sum(ws) > 0)
    assert allocate(total, ws) == reference(total, ws)


@given(totals, weights)
def test_never_loses_a_cent(total, ws):
    assume(sum(ws) > 0)
    assert sum(allocate(total, ws)) == total


def test_largest_remainder_wins_over_index():
    assert allocate(10, [1, 2]) == [3, 7]


@pytest.mark.parametrize("total, ws", [(-1, [1]), (10, []), (10, [0, 0]), (10, [2, -1])])
def test_rejects_invalid_input(total, ws):
    with pytest.raises(ValueError):
        allocate(total, ws)
