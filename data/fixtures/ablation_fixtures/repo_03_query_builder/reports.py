"""Reporting metrics query generator."""

from __future__ import annotations

from typing import Any
from schema_whitelist import validate_table_whitelist


def build_metric_query(requested_table: str, metric_category: str) -> tuple[str, list[Any]]:
    """Build dynamic aggregation query with validated table name and parameterized filters.

    Uses `schema_whitelist.validate_table_whitelist` to ensure table name is strictly
    from the trusted enumeration, preventing SQL injection on identifier interpolation.
    """
    safe_table = validate_table_whitelist(requested_table)

    # Table identifier is verified against whitelist; metric parameter is parameterized
    sql = f"SELECT count(*), max(recorded_at) FROM {safe_table} WHERE category = %s"
    params = [metric_category]

    return sql, params
