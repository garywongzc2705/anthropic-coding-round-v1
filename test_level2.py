"""
Level 2 — Per-Key Rate Limiting

Extend your RateLimiter to track limits independently per client key.
A "key" is any string identifier — an API key, user ID, IP address, etc.

Changes to the interface:
  allow(key)      — returns True/False for this specific key
  remaining(key)  — remaining requests for this key
  reset_in(key)   — seconds until this key's window resets

Semantics:
  - Each key gets its own independent counter and window
  - A key that has never been seen behaves as if it has made 0 requests
  - Keys do not affect each other
  - All keys share the same max_requests and window_seconds configuration
  - The clock is still global (shared across all keys)
  - Memory: you do not need to evict old keys in this level
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


# --- Basic per-key isolation ---


def test_different_keys_are_independent():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=2, window_seconds=60)
    r.set_clock(clock)
    r.allow("alice")
    r.allow("alice")
    assert r.allow("alice") is False
    assert r.allow("bob") is True


def test_unknown_key_starts_fresh():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    r.allow("alice")
    r.allow("alice")
    r.allow("alice")
    assert r.allow("carol") is True


def test_remaining_per_key():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    r.allow("alice")
    r.allow("alice")
    r.allow("bob")
    assert r.remaining("alice") == 1
    assert r.remaining("bob") == 2


def test_remaining_unknown_key_is_max():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=5, window_seconds=60)
    r.set_clock(clock)
    assert r.remaining("unknown") == 5


def test_reset_in_per_key_same_window():
    clock, advance = make_clock(start=0.0)
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    r.allow("alice")
    advance(20)
    r.allow("bob")
    assert r.reset_in("alice") == r.reset_in("bob")


# --- Window reset per key ---


def test_window_reset_per_key():
    clock, advance = make_clock()
    r = RateLimiter(max_requests=2, window_seconds=60)
    r.set_clock(clock)
    r.allow("alice")
    r.allow("alice")
    advance(60)
    assert r.allow("alice") is True
    assert r.remaining("alice") == 1


def test_window_reset_does_not_affect_other_keys():
    clock, advance = make_clock()
    r = RateLimiter(max_requests=2, window_seconds=60)
    r.set_clock(clock)
    r.allow("alice")
    r.allow("bob")
    advance(60)
    assert r.remaining("alice") == 2
    assert r.remaining("bob") == 2


# --- Multiple keys, multiple windows ---


def test_many_keys():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=1, window_seconds=60)
    r.set_clock(clock)
    keys = [f"user_{i}" for i in range(100)]
    for key in keys:
        assert r.allow(key) is True
    for key in keys:
        assert r.allow(key) is False


def test_zero_limit_applies_to_all_keys():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=0, window_seconds=60)
    r.set_clock(clock)
    assert r.allow("alice") is False
    assert r.allow("bob") is False
    assert r.remaining("alice") == 0
