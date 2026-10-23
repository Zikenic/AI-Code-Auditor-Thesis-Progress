"""Buggy Fixture: CAND-0005
Category 1: Boundary / Logic / Control Flow
Primary CWE: CWE-125 (Out-of-bounds Read)
"""

from __future__ import annotations

def binary_search_lookup(sorted_arr: list[int], target: int) -> int | None:
    """Perform binary search and return element index."""
    low = 0
    high = len(sorted_arr)
    while low <= high:
        mid = (low + high) // 2
        if sorted_arr[mid] == target:
            return mid
        elif sorted_arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return None
