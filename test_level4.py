"""
Level 4 — Sliding Window

The fixed window limiter has a well-known edge case: a client can make
max_requests at the end of window N and max_requests at the start of
window N+1, effectively doubling the allowed rate at the boundary.

Add a sliding window mode that eliminates this burst.

New constructor parameter:
  RateLimiter(max_requests, window_seconds, mode='fixed')

  mode='fixed'   — existing behavior (default, all previous tests must pass)
  mode='sliding' — sliding window: at any point in time, the number of
                   requests in the last window_seconds must not exceed
                   max_requests

Sliding window semantics:
  - allow(key) checks if the count of requests in [now - window_seconds, now)
    is less than max_requests. If yes, records the request and returns True.
  - The window is per-key, same as fixed mode.
  - remaining(key) returns max_requests minus requests in the current
    sliding window.
  - reset_in(key) returns the number of seconds until the oldest request
    in the window expires (freeing one slot). Returns 0.0 if not at limit,
    or window_seconds if no requests have been made.
  - Per-key limit overrides (set_limit) must work in sliding mode too.
  - The clock injection (set_clock) works the same way.

Implementation note:
  Sliding window requires storing individual request timestamps per key.
  You will need to evict expired timestamps on each operation.
  stdlib only — no external libraries.
"""

import pytest
from solution_level2 import RateLimiter


def make_clock(start=0.0):
    t = [start]

    def clock():
        return t[0]

    def advance(seconds):
        t[0] += seconds

    return clock, advance


# --- Fixed mode still works (regression) ---


def test_fixed_mode_default():
    clock, advance = make_clock()
    r = RateLimiter(max_requests=2, window_seconds=60)
    r.set_clock(clock)
    r.allow("alice")
    r.allow("alice")
    assert r.allow("alice") is False
    advance(60)
    assert r.allow("alice") is True


# --- Basic sliding window ---


def test_sliding_allows_up_to_limit():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60, mode="sliding")
    r.set_clock(clock)
    assert r.allow("alice") is True
    assert r.allow("alice") is True
    assert r.allow("alice") is True
    assert r.allow("alice") is False


def test_sliding_window_expires_old_requests():
    clock, advance = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60, mode="sliding")
    r.set_clock(clock)
    r.allow("alice")
    r.allow("alice")
    r.allow("alice")
    assert r.allow("alice") is False
    advance(61)
    assert r.allow("alice") is True


def test_sliding_window_partial_expiry():
    clock, advance = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60, mode="sliding")
    r.set_clock(clock)
    r.allow("alice")
    advance(30)
    r.allow("alice")
    r.allow("alice")
    assert r.allow("alice") is False
    advance(31)
    assert r.allow("alice") is True
    assert r.allow("alice") is False


def test_sliding_eliminates_boundary_burst():
    clock, advance = make_clock(start=50.0)
    r = RateLimiter(max_requests=3, window_seconds=60, mode="sliding")
    r.set_clock(clock)
    r.allow("alice")
    r.allow("alice")
    r.allow("alice")
    advance(11)
    assert r.allow("alice") is False


def test_fixed_allows_boundary_burst():
    clock, advance = make_clock(start=50.0)
    r = RateLimiter(max_requests=3, window_seconds=60, mode="fixed")
    r.set_clock(clock)
    r.allow("alice")
    r.allow("alice")
    r.allow("alice")
    advance(11)
    assert r.allow("alice") is True


# --- remaining() and reset_in() in sliding mode ---


def test_sliding_remaining_decrements():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60, mode="sliding")
    r.set_clock(clock)
    r.allow("alice")
    assert r.remaining("alice") == 2


def test_sliding_remaining_recovers_as_window_slides():
    clock, advance = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60, mode="sliding")
    r.set_clock(clock)
    r.allow("alice")
    r.allow("alice")
    r.allow("alice")
    assert r.remaining("alice") == 0
    advance(61)
    assert r.remaining("alice") == 3


def test_sliding_reset_in_no_requests():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60, mode="sliding")
    r.set_clock(clock)
    assert r.reset_in("alice") == 60.0


def test_sliding_reset_in_at_limit():
    clock, advance = make_clock(start=0.0)
    r = RateLimiter(max_requests=2, window_seconds=60, mode="sliding")
    r.set_clock(clock)
    r.allow("alice")
    advance(10)
    r.allow("alice")
    assert r.allow("alice") is False
    assert r.reset_in("alice") == 50.0


def test_sliding_reset_in_not_at_limit():
    clock, advance = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60, mode="sliding")
    r.set_clock(clock)
    r.allow("alice")
    advance(10)
    assert r.reset_in("alice") == 0.0


# --- Per-key isolation in sliding mode ---


def test_sliding_keys_are_independent():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=2, window_seconds=60, mode="sliding")
    r.set_clock(clock)
    r.allow("alice")
    r.allow("alice")
    assert r.allow("alice") is False
    assert r.allow("bob") is True


# --- set_limit works in sliding mode ---


def test_sliding_set_limit_override():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=2, window_seconds=60, mode="sliding")
    r.set_clock(clock)
    r.set_limit("vip", 5)
    for _ in range(5):
        assert r.allow("vip") is True
    assert r.allow("vip") is False
