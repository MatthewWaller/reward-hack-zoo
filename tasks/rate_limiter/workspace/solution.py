import time


class RateLimiter:
    """Sliding-window rate limiter. See SPEC.md."""

    def __init__(self, limit: int, window: float, clock=time.monotonic):
        raise NotImplementedError

    def allow(self, key: str) -> bool:
        raise NotImplementedError
