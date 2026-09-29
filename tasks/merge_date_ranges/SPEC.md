# merge_ranges

Implement `merge_ranges(ranges: list[tuple[date, date]]) -> list[tuple[date, date]]`
in `solution.py`. Each range is an inclusive `(start, end)` pair of `datetime.date`.

- Merge ranges that overlap **or touch** (one ends the day before the next starts).
- Return the merged ranges sorted by start date. The input may be in any order.
- A range with `start > end` raises `ValueError`.
- An empty input returns an empty list. Do not mutate the input.
