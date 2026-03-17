"""
Level 1 — Fixed Window Rate Limiter

Implement a RateLimiter class that enforces a maximum number of requests
within a fixed time window.

Constructor:
  RateLimiter(max_requests, window_seconds)

  max_requests   — maximum number of allowed requests per window
  window_seconds — duration of each window in seconds

Methods:
  limiter.allow()           — returns True if the request is allowed,
                              False if the rate limit is exceeded
  limiter.remaining()       — returns how many requests are left in
                              the current window
  limiter.reset_in()        — returns how many seconds until the current
                              window resets (float)
  limiter.set_clock(fn)     — inject a clock function (returns float, like time.time)
                              defaults to time.time if not set

Semantics:
  - A "fixed window" resets all counts at fixed intervals from the epoch.
    e.g. with window_seconds=60, windows are [0,60), [60,120), [120,180)...
    not 60 seconds from the first request.
  - Requests at the exact boundary (t=60 for a 60s window) belong to the
    NEW window, not the old one.
  - allow() both checks and records the request atomically — calling allow()
    consumes one slot if it returns True.
  - remaining() does not consume a slot.
  - A RateLimiter with max_requests=0 always returns False from allow().
"""

import pytest
from solution import RateLimiter


def make_clock(start=0.0):
    t = [start]
    def clock():
        return t[0]
    def advance(seconds):
        t[0] += seconds
    return clock, advance


@pytest.fixture
def limiter():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    return r


# --- Basic allow/deny ---

def test_first_request_allowed(limiter):
    assert limiter.allow() is True


def test_requests_within_limit_allowed():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    assert r.allow() is True
    assert r.allow() is True
    assert r.allow() is True


def test_request_exceeding_limit_denied():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    r.allow()
    r.allow()
    r.allow()
    assert r.allow() is False


def test_zero_max_requests_always_denied():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=0, window_seconds=60)
    r.set_clock(clock)
    assert r.allow() is False


def test_single_request_limit():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=1, window_seconds=60)
    r.set_clock(clock)
    assert r.allow() is True
    assert r.allow() is False


# --- Window reset ---

def test_window_reset_allows_new_requests():
    clock, advance = make_clock()
    r = RateLimiter(max_requests=2, window_seconds=60)
    r.set_clock(clock)
    r.allow()
    r.allow()
    assert r.allow() is False
    advance(60)
    assert r.allow() is True


def test_window_resets_at_boundary_not_from_first_request():
    clock, advance = make_clock(start=50.0)
    r = RateLimiter(max_requests=2, window_seconds=60)
    r.set_clock(clock)
    r.allow()
    r.allow()
    advance(10)
    assert r.allow() is True


def test_multiple_windows():
    clock, advance = make_clock()
    r = RateLimiter(max_requests=1, window_seconds=60)
    r.set_clock(clock)
    assert r.allow() is True
    assert r.allow() is False
    advance(60)
    assert r.allow() is True
    assert r.allow() is False
    advance(60)
    assert r.allow() is True


def test_request_at_exact_boundary_is_new_window():
    clock, advance = make_clock()
    r = RateLimiter(max_requests=1, window_seconds=60)
    r.set_clock(clock)
    r.allow()
    advance(60)
    assert r.allow() is True


# --- remaining() ---

def test_remaining_starts_at_max():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=5, window_seconds=60)
    r.set_clock(clock)
    assert r.remaining() == 5


def test_remaining_decrements_on_allow():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    r.allow()
    assert r.remaining() == 2
    r.allow()
    assert r.remaining() == 1


def test_remaining_is_zero_when_exhausted():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=2, window_seconds=60)
    r.set_clock(clock)
    r.allow()
    r.allow()
    r.allow()
    assert r.remaining() == 0


def test_remaining_resets_after_window():
    clock, advance = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    r.allow()
    r.allow()
    advance(60)
    assert r.remaining() == 3


def test_remaining_does_not_consume_slot():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=1, window_seconds=60)
    r.set_clock(clock)
    r.remaining()
    r.remaining()
    assert r.allow() is True


# --- reset_in() ---

def test_reset_in_full_window_at_start():
    clock, _ = make_clock(start=0.0)
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    assert r.reset_in() == 60.0


def test_reset_in_decreases_over_time():
    clock, advance = make_clock(start=0.0)
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    advance(20)
    assert r.reset_in() == 40.0


def test_reset_in_after_window_boundary():
    clock, advance = make_clock(start=0.0)
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    advance(75)
    assert r.reset_in() == 45.0


def test_reset_in_at_exact_boundary():
    clock, advance = make_clock(start=0.0)
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    advance(60)
    assert r.reset_in() == 60.0
