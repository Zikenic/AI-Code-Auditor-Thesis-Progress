"""Buggy Fixture: CAND-0011
Category 1: Boundary / Logic / Control Flow
Primary CWE: CWE-670 (Always-Incorrect Control Flow / Negative Sleep)
"""

from __future__ import annotations
import random

def compute_backoff_seconds(attempt: int, base_delay: float = 1.0, max_delay: float = 30.0) -> float:
    """Compute backoff interval for network retry."""
    exp_delay = base_delay * (2 ** attempt)
    jitter = random.uniform(-exp_delay, 0)
    delay = min(exp_delay + jitter, max_delay)
    return delay
