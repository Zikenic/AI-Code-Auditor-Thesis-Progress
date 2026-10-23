"""Clean Control Fixture: CTRL-0007
Paired with: CAND-0014 (Category 3: Database & SQL Injection)
Target Scope: Database query construction with parameterized date filters
Intended Behavior: Uses SQL placeholders (%s) and parameter binding instead of string
concatenation, eliminating SQL Injection (CWE-89).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def build_audit_log_query(start_date: datetime, end_date: datetime, user_id: int) -> tuple[str, list[Any]]:
    """Construct SQL query with parameter binding for date-filtered audit records."""
    query = (
        "SELECT id, action, created_at, user_id "
        "FROM audit_events "
        "WHERE created_at >= %s AND created_at <= %s AND user_id = %s "
        "ORDER BY created_at DESC LIMIT 100"
    )
    params = [start_date.isoformat(), end_date.isoformat(), int(user_id)]
    return query, params
