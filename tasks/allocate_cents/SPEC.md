# allocate

Implement `allocate(total_cents: int, weights: list[int]) -> list[int]` in
`solution.py`. It splits an amount of money in proportion to integer weights,
without creating or losing a cent.

- Each share starts as `floor(total_cents * weight / sum(weights))`.
- The leftover cents are handed out one at a time to the shares with the
  largest fractional remainder. Ties go to the earlier index.
- The result always sums to exactly `total_cents`.
- Raise `ValueError` if `total_cents` is negative, `weights` is empty, any
  weight is negative, or all weights are zero.
