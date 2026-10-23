"""SQL schema whitelist validation helper."""

from __future__ import annotations

ALLOWED_METRIC_TABLES: frozenset[str] = frozenset({
    "daily_active_users",
    "monthly_revenue_summary",
    "audit_trail_events",
    "system_error_logs",
})


def validate_table_whitelist(table_identifier: str) -> str:
    """Validate dynamic table name against an immutable whitelist.

    Prevents SQL injection when dynamic table identifiers must be formatted
    into query templates where database drivers do not support parameterized identifiers.
    """
    if not table_identifier:
        raise ValueError("Table name must not be empty")

    normalized = str(table_identifier).strip().lower()
    if normalized not in ALLOWED_METRIC_TABLES:
        raise ValueError(f"Table identifier '{table_identifier}' is not in allowed reporting whitelist")

    return normalized
