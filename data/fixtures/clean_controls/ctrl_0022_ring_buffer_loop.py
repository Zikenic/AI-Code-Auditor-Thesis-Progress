"""Clean Control Fixture: CTRL-0022
Paired with: CAND-0010 (Category 1: Boundary / Logic / Control Flow)
Target Scope: Circular buffer drain loop termination
Intended Behavior: Decrements item count cleanly to guarantee loop termination.
"""

from __future__ import annotations

class CircularDrainBuffer:
    def __init__(self, size: int = 8):
        self.size = size
        self.buffer = [None] * size
        self.head = 0
        self.count = 0

    def drain_all(self) -> list[int]:
        """Drain all elements using explicit item counter."""
        items = []
        while self.count > 0:
            items.append(self.buffer[self.head])
            self.head = (self.head + 1) % self.size
            self.count -= 1
        return items
