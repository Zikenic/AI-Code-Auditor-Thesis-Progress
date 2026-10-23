"""Clean Control Fixture: CTRL-0023
Paired with: CAND-0011 (Category 1: Boundary / Logic / Control Flow)
Target Scope: Exponential backoff calculation with jitter
Intended Behavior: Enforces non-negative lower bound on jittered delay.
"""

from __future__ import annotations
import random

def compute_backoff_seconds(attempt: int, base_delay: float = 1.0, max_delay: float = 30.0) -> float:
    """Compute guaranteed non-negative backoff interval."""
    exp_delay = min(base_delay * (2 ** max(0, attempt)), max_delay)
    jitter = random.uniform(0, exp_delay * 0.5)
    return max(0.1, min(exp_delay + jitter, max_delay))
