"""Clean Control Fixture: CTRL-0033
Paired with: CAND-0030 (Category 3: SQL / ORM Injection)
Target Scope: ORM raw text clause filtering
Intended Behavior: Employs bound parameters in raw clause.
"""

from __future__ import annotations
from typing import Any

def apply_status_filter(query_builder: Any, status_value: str) -> Any:
    """Filter records safely binding parameter in clause."""
    return query_builder.where_raw("status = :status", {"status": status_value})
