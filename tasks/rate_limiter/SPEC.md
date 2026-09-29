# RateLimiter

Implement a sliding-window rate limiter in `solution.py`:

```python
class RateLimiter:
    def __init__(self, limit: int, window: float, clock=time.monotonic): ...
    def allow(self, key: str) -> bool: ...
```

- `allow(key)` returns `True` and records the call when fewer than `limit` calls
  for that key were **allowed** in the last `window` seconds. Otherwise it
  returns `False`.
- A call made at time `t` counts while `clock() - t < window`.
- Denied calls are not recorded and do not extend the wait.
- Keys are independent.
- `clock` is a zero-argument function returning seconds; tests may inject a fake.
