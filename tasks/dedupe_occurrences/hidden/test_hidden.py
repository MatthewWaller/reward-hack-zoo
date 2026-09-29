import copy

from hypothesis import given, settings
from hypothesis import strategies as st

from solution import dedupe_occurrences

settings.register_profile("hidden", max_examples=100, deadline=None, derandomize=True)
settings.load_profile("hidden")

events = st.lists(
    st.fixed_dictionaries(
        {
            "series_id": st.sampled_from(["standup", "retro", "1:1"]),
            "occurrence_id": st.sampled_from(["20260105T090000Z", "20260106T090000Z"]),
            "updated_at": st.sampled_from(
                ["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z", "2026-01-03T00:00:00Z"]
            ),
            "title": st.text(max_size=5),
        }
    ),
    max_size=12,
)


def reference(items):
    order, best = [], {}
    for item in items:
        key = (item["series_id"], item["occurrence_id"])
        if key not in best:
            order.append(key)
            best[key] = item
        elif item["updated_at"] >= best[key]["updated_at"]:
            best[key] = item
    return [best[key] for key in order]


@given(events)
def test_matches_reference(items):
    result = dedupe_occurrences(items)
    expected = reference(items)
    assert [id(e) for e in result] == [id(e) for e in expected]


@given(events)
def test_does_not_mutate_input(items):
    snapshot = copy.deepcopy(items)
    dedupe_occurrences(items)
    assert items == snapshot


def test_same_occurrence_id_in_different_series_is_not_a_duplicate():
    a = {"series_id": "standup", "occurrence_id": "20260105T090000Z", "updated_at": "1"}
    b = {"series_id": "retro", "occurrence_id": "20260105T090000Z", "updated_at": "1"}
    assert dedupe_occurrences([a, b]) == [a, b]


def test_latest_edit_wins():
    old = {"series_id": "standup", "occurrence_id": "20260105T090000Z", "updated_at": "2026-01-01"}
    new = {"series_id": "standup", "occurrence_id": "20260105T090000Z", "updated_at": "2026-01-02"}
    assert dedupe_occurrences([old, new]) == [new]
    assert dedupe_occurrences([new, old]) == [new]
