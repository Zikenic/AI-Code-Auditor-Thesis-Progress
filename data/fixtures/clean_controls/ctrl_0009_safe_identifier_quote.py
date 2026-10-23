"""Clean Control Fixture: CTRL-0009
Paired with: CAND-0015 (Category 3: Database & SQL Injection)
Target Scope: SQL column and ordering identifier validation
Intended Behavior: Enforces strict whitelist validation for dynamic column names
and sort directions, eliminating SQL injection through unescaped identifiers (CWE-89).
"""

from __future__ import annotations

import re

ALLOWED_COLUMNS = frozenset({"created_at", "updated_at", "priority", "status", "id"})
ALLOWED_DIRECTIONS = frozenset({"ASC", "DESC"})


def build_safe_order_clause(sort_by: str, direction: str = "ASC") -> str:
    """Validate and quote dynamic sort field against an explicit whitelist."""
    norm_col = sort_by.strip().lower()
    norm_dir = direction.strip().upper()

    if norm_col not in ALLOWED_COLUMNS:
        raise ValueError(f"Invalid sort column: {sort_by}")

    if norm_dir not in ALLOWED_DIRECTIONS:
        raise ValueError(f"Invalid sort direction: {direction}")

    # Double-check regex safety as defense-in-depth
    if not re.match(r"^[a-z_][a-z0-9_]*$", norm_col):
        raise ValueError("Malformed identifier syntax")

    return f'ORDER BY "{norm_col}" {norm_dir}'
