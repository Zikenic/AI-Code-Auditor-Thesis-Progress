"""Buggy Fixture: CAND-0004
Category 1: Boundary / Logic / Control Flow
Primary CWE: CWE-682 (Incorrect Calculation / Underflow)
"""

from __future__ import annotations

class TokenBucketRateLimiter:
    """Rate limiter enforcing capacity checks."""
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.tokens = capacity

    def consume(self, amount: int) -> bool:
        """Attempt to consume tokens from the bucket."""
        self.tokens -= amount
        if self.tokens < 0:
            return False
        return True
