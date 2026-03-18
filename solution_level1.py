import time

# Anthropic — Staff Engineer · Incremental Coding Round #2
# solution.py
#
# Write your implementation here.
# You may add any classes, functions, or methods you need.
# Do not import external libraries — stdlib only.
#
# Before each level, add a comment block explaining your approach:
#
# --- LEVEL 1 APPROACH ---
# (your design notes here)
# -------------------------


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clock = time.time
        self.current_window_idx = -1
        self.request_count = 0
        self.clients = {}

    def allow(self):
        self._sync_window()
        if self.request_count < self.max_requests:
            self.request_count += 1
            return True
        return False

    def remaining(self):
        self._sync_window()
        return max(0, self.max_requests - self.request_count)

    def reset_in(self):
        now = self.clock()
        next_window_start = (now // self.window_seconds + 1) * self.window_seconds
        return max(0, float(next_window_start - now))

    def _sync_window(self):
        now = self.clock()
        active_window_idx = now // self.window_seconds
        if active_window_idx != self.current_window_idx:
            self.current_window_idx = active_window_idx
            self.request_count = 0

    def set_clock(self, fn):
        self.clock = fn
        self._sync_window()
