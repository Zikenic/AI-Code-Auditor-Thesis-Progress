"""Buggy Fixture: CAND-0003
Category 1: Boundary / Logic / Control Flow
Primary CWE: CWE-193 (Off-by-one Error)
"""

from __future__ import annotations
from typing import Any

def paginate_records(records: list[Any], page: int, page_size: int = 10) -> list[Any]:
    """Retrieve requested page slice from in-memory records."""
    start_index = (page - 1) * page_size + 1
    end_index = start_index + page_size
    return records[start_index:end_index]
