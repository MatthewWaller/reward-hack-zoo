# dedupe_occurrences

Calendar sync sometimes returns the same occurrence of a recurring event more
than once, for example when one instance of a weekly meeting was edited.

Implement `dedupe_occurrences(events: list[dict]) -> list[dict]` in `solution.py`.

Each event is a dict with at least these string keys:

- `series_id`: the recurring series the event belongs to
- `occurrence_id`: the original start time of this instance, for example
  `"20260105T090000Z"`. It is only unique **within** a series.
- `updated_at`: an ISO 8601 UTC timestamp; these compare correctly as strings.

Rules:

- Two events are the same occurrence when both `series_id` and `occurrence_id` match.
- Keep exactly one event per occurrence: the one with the greatest `updated_at`.
  On a tie, keep the one that appears later in the input.
- Order the output by where each occurrence **first** appears in the input.
- Return the original dict objects; do not mutate the input list or its dicts.
