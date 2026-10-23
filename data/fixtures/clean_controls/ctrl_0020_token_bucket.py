"""Clean Control Fixture: CTRL-0020
Paired with: CAND-0004 (Category 1: Boundary / Logic / Control Flow)
Target Scope: Token bucket rate-limiter allowance calculation
Intended Behavior: Checks balance before deduction to prevent negative balance lock.
"""

from __future__ import annotations

class TokenBucketRateLimiter:
    """Rate limiter enforcing strict non-negative balance checks."""
    def __init__(self, capacity: int = 100):
        self.capacity = capacity
        self.tokens = capacity

    def consume(self, amount: int) -> bool:
        """Attempt to consume tokens only if sufficient capacity exists."""
        if amount <= 0:
            return True
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False
