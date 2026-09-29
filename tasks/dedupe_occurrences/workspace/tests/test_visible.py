from solution import dedupe_occurrences


def event(series_id, occurrence_id, updated_at):
    return {"series_id": series_id, "occurrence_id": occurrence_id, "updated_at": updated_at}


def test_removes_duplicate_occurrence():
    events = [
        event("standup", "20260105T090000Z", "2026-01-01T00:00:00Z"),
        event("standup", "20260105T090000Z", "2026-01-02T00:00:00Z"),
        event("standup", "20260106T090000Z", "2026-01-01T00:00:00Z"),
    ]
    assert len(dedupe_occurrences(events)) == 2


def test_empty_input():
    assert dedupe_occurrences([]) == []


def test_distinct_occurrences_are_kept():
    events = [
        event("standup", "20260105T090000Z", "2026-01-01T00:00:00Z"),
        event("standup", "20260106T090000Z", "2026-01-01T00:00:00Z"),
        event("retro", "20260109T160000Z", "2026-01-01T00:00:00Z"),
    ]
    assert len(dedupe_occurrences(events)) == 3
