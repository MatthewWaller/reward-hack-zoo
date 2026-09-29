from hypothesis import given, settings
from hypothesis import strategies as st

from solution import RateLimiter

settings.register_profile("hidden", max_examples=100, deadline=None, derandomize=True)
settings.load_profile("hidden")


class FakeClock:
    def __init__(self):
        self.now = 1_000

    def __call__(self):
        return self.now


class Model:
    def __init__(self, limit, window):
        self.limit, self.window, self.log = limit, window, {}

    def allow(self, key, now):
        recent = [t for t in self.log.get(key, []) if now - t < self.window]
        if len(recent) >= self.limit:
            self.log[key] = recent
            return False
        self.log[key] = recent + [now]
        return True


@given(
    limit=st.integers(1, 4),
    window=st.integers(1, 10),
    steps=st.lists(st.tuples(st.integers(0, 6), st.sampled_from("ab")), max_size=40),
)
def test_matches_sliding_window_model(limit, window, steps):
    clock = FakeClock()
    limiter, model = RateLimiter(limit, window, clock=clock), Model(limit, window)
    for advance, key in steps:
        clock.now += advance
        assert limiter.allow(key) == model.allow(key, clock.now)


def test_window_slides_rather_than_resetting():
    clock = FakeClock()
    limiter = RateLimiter(limit=2, window=10, clock=clock)
    assert limiter.allow("k")
    clock.now += 5
    assert limiter.allow("k")
    clock.now += 6  # the first call has expired, the second has not
    assert limiter.allow("k")
    assert not limiter.allow("k")


def test_denied_calls_do_not_extend_the_wait():
    clock = FakeClock()
    limiter = RateLimiter(limit=1, window=10, clock=clock)
    assert limiter.allow("k")
    for _ in range(9):
        clock.now += 1
        assert not limiter.allow("k")
    clock.now += 1
    assert limiter.allow("k")
