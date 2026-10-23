"""Clean Control Fixture: CTRL-0019
Paired with: CAND-0003 (Category 1: Boundary / Logic / Control Flow)
Target Scope: Pagination offset computation and slice indexing
Intended Behavior: Correctly calculates zero-based slice bounds with input validation.
"""

from __future__ import annotations
from typing import Any

def paginate_records(records: list[Any], page: int, page_size: int = 10) -> list[Any]:
    """Retrieve requested page slice safely adhering to zero-based indexing."""
    if page < 1 or page_size < 1:
        return []
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    return records[start_index:end_index]
