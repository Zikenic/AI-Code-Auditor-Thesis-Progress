"""Clean Control Fixture: CTRL-0021
Paired with: CAND-0005 (Category 1: Boundary / Logic / Control Flow)
Target Scope: Binary search index boundary clamp
Intended Behavior: Enforces strict upper bound checks to prevent IndexError.
"""

from __future__ import annotations

def binary_search_lookup(sorted_arr: list[int], target: int) -> int | None:
    """Perform binary search safely within array bounds."""
    low = 0
    high = len(sorted_arr) - 1
    while low <= high:
        mid = (low + high) // 2
        val = sorted_arr[mid]
        if val == target:
            return mid
        elif val < target:
            low = mid + 1
        else:
            high = mid - 1
    return None
