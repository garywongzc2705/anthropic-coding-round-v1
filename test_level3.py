"""
Level 3 — Per-Key Limit Overrides

Add the ability to set custom rate limits for specific keys, overriding
the global default configured at construction time.

New method:
  limiter.set_limit(key, max_requests)  — override the max_requests for
                                          this specific key only.
                                          window_seconds stays the same.

Semantics:
  - Keys without an override use the global max_requests
  - set_limit() can be called before or after the key has made requests
  - Calling set_limit() mid-window takes effect immediately:
      if a key has used 8/10 requests and you lower the limit to 5,
      remaining() returns 0 and allow() returns False immediately
  - Calling set_limit() with a higher limit mid-window gives the key
      access to the new headroom immediately
  - set_limit() called with the same value as the global default is fine —
      treat it as an explicit override that happens to match the default
  - A key's override persists across window resets
  - Calling set_limit() on a key that has never made a request is valid —
      that key will use the override when it eventually makes requests
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


# --- Basic overrides ---


def test_set_limit_overrides_default():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    r.set_limit("premium", 10)
    for _ in range(10):
        assert r.allow("premium") is True
    assert r.allow("premium") is False


def test_default_key_unaffected_by_override():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    r.set_limit("premium", 10)
    r.allow("free")
    r.allow("free")
    r.allow("free")
    assert r.allow("free") is False


def test_remaining_reflects_override():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    r.set_limit("vip", 100)
    assert r.remaining("vip") == 100


def test_remaining_default_unaffected():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    r.set_limit("vip", 100)
    assert r.remaining("regular") == 3


# --- set_limit mid-window ---


def test_lower_limit_mid_window_takes_effect_immediately():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=10, window_seconds=60)
    r.set_clock(clock)
    for _ in range(8):
        r.allow("alice")
    r.set_limit("alice", 5)
    assert r.remaining("alice") == 0
    assert r.allow("alice") is False


def test_raise_limit_mid_window_gives_headroom():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    r.allow("alice")
    r.allow("alice")
    r.allow("alice")
    assert r.allow("alice") is False
    r.set_limit("alice", 10)
    assert r.remaining("alice") == 7
    assert r.allow("alice") is True


def test_lower_limit_below_used_clamps_remaining_to_zero():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=10, window_seconds=60)
    r.set_clock(clock)
    for _ in range(6):
        r.allow("alice")
    r.set_limit("alice", 3)
    assert r.remaining("alice") == 0


# --- Override persists across window resets ---


def test_override_persists_after_window_reset():
    clock, advance = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    r.set_limit("premium", 10)
    for _ in range(10):
        r.allow("premium")
    advance(60)
    assert r.remaining("premium") == 10


def test_default_key_persists_correctly_after_window():
    clock, advance = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    r.set_limit("premium", 10)
    r.allow("free")
    advance(60)
    assert r.remaining("free") == 3


# --- Override before first request ---


def test_set_limit_before_any_requests():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=3, window_seconds=60)
    r.set_clock(clock)
    r.set_limit("new_user", 1)
    assert r.allow("new_user") is True
    assert r.allow("new_user") is False


def test_multiple_overrides_independent():
    clock, _ = make_clock()
    r = RateLimiter(max_requests=5, window_seconds=60)
    r.set_clock(clock)
    r.set_limit("alice", 1)
    r.set_limit("bob", 100)
    assert r.allow("alice") is True
    assert r.allow("alice") is False
    assert r.remaining("bob") == 100
    assert r.remaining("charlie") == 5
