# parse_duration

Implement `parse_duration(text: str) -> int` in `solution.py`. It returns the
total number of seconds in a compact duration string.

- The input is one or more components of the form `<digits><unit>`.
- Units are `d` (86400 seconds), `h` (3600), `m` (60) and `s` (1).
- Units must appear in that order (`d` before `h` before `m` before `s`) and
  each at most once. Digits are ASCII `0-9`; leading zeros are allowed.
- No whitespace, signs, decimals or uppercase units.
- Anything else, including the empty string, raises `ValueError`.

Examples: `"90s"` is 90, `"1d2h"` is 93600, `"1m1h"` raises `ValueError`.
