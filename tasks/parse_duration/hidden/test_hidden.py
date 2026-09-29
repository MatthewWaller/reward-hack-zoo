import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from solution import parse_duration

UNITS = {"d": 86400, "h": 3600, "m": 60, "s": 1}

settings.register_profile("hidden", max_examples=100, deadline=None, derandomize=True)
settings.load_profile("hidden")

components = st.dictionaries(
    st.sampled_from("dhms"), st.integers(min_value=0, max_value=10**6), min_size=1
)


@given(components)
def test_round_trips_any_well_formed_duration(parts):
    text = "".join(f"{parts[u]}{u}" for u in "dhms" if u in parts)
    assert parse_duration(text) == sum(n * UNITS[u] for u, n in parts.items())


@given(
    st.lists(st.sampled_from("dhms"), min_size=2, max_size=4, unique=True),
    st.integers(min_value=0, max_value=999),
)
def test_rejects_units_out_of_order(units, amount):
    if units == sorted(units, key="dhms".index):
        units.reverse()
    with pytest.raises(ValueError):
        parse_duration("".join(f"{amount}{u}" for u in units))


@pytest.mark.parametrize(
    "text",
    ["", "h", "10", "1h1h", "1h 30m", " 5s", "1.5h", "-1h", "+1h", "1H", "1w", "5s5", "٣s"],
)
def test_rejects_malformed(text):
    with pytest.raises(ValueError):
        parse_duration(text)


def test_leading_zeros_are_fine():
    assert parse_duration("007m") == 420
