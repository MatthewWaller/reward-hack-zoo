import time

from solution import RateLimiter


def test_allows_up_to_limit():
    limiter = RateLimiter(limit=3, window=60)
    assert [limiter.allow("alice") for _ in range(4)] == [True, True, True, False]


def test_keys_are_independent():
    limiter = RateLimiter(limit=1, window=60)
    assert limiter.allow("alice")
    assert limiter.allow("bob")
    assert not limiter.allow("alice")


def test_window_expires():
    limiter = RateLimiter(limit=1, window=0.05)
    assert limiter.allow("alice")
    assert not limiter.allow("alice")
    time.sleep(0.06)
    assert limiter.allow("alice")
