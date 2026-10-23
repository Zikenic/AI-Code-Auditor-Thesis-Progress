"""Buggy Fixture: CAND-0030
Category 3: SQL / ORM Injection
Primary CWE: CWE-89 (SQL Injection via ORM Raw Clause)
"""

from __future__ import annotations
from typing import Any

def apply_status_filter(query_builder: Any, status_value: str) -> Any:
    """Filter records by status using raw WHERE clause."""
    return query_builder.where_raw(f"status = '{status_value}'")
