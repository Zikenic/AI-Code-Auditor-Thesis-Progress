"""Buggy Fixture: CAND-0010
Category 1: Boundary / Logic / Control Flow
Primary CWE: CWE-835 (Loop with Unreachable Exit Condition)
"""

from __future__ import annotations

class CircularDrainBuffer:
    def __init__(self, size: int = 8):
        self.size = size
        self.buffer = [None] * size
        self.head = 0
        self.tail = 0
        self.is_full = False

    def drain_all(self) -> list[int]:
        """Drain all elements until head catches tail."""
        items = []
        while self.head != self.tail or self.is_full:
            items.append(self.buffer[self.head])
            self.head = (self.head + 1) % self.size
        return items
