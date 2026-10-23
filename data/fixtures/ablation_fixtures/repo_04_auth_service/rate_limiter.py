"""In-memory rate limiter helper for sensitive authentication endpoints."""

from __future__ import annotations

import time
from collections import defaultdict


class RateLimitExceeded(PermissionError):
    """Raised when an identifier exceeds allowed attempts within window."""
    pass


class SlidingWindowRateLimiter:
    """Sliding-window counter rate limiter protecting against brute-force attacks."""

    def __init__(self, max_attempts: int = 5, window_seconds: float = 60.0):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._history: dict[str, list[float]] = defaultdict(list)

    def check_and_record(self, key: str) -> None:
        """Record attempt for key and raise RateLimitExceeded if threshold breached."""
        now = time.monotonic()
        cutoff = now - self.window_seconds

        # Prune expired timestamps
        active = [t for t in self._history[key] if t > cutoff]
        if len(active) >= self.max_attempts:
            raise RateLimitExceeded(
                f"Rate limit exceeded for key '{key}': max {self.max_attempts} attempts per {self.window_seconds}s"
            )

        active.append(now)
        self._history[key] = active
