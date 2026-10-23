"""Clean Control Fixture: CTRL-0030
Paired with: CAND-0024 (Category 3: SQL / ORM Injection)
Target Scope: Dynamic query sorting clause generation
Intended Behavior: Validates sorting column against strict whitelist.
"""

from __future__ import annotations
import sqlite3

ALLOWED_SORT_COLUMNS = {"id", "title", "created_at"}

def get_sorted_records(conn: sqlite3.Connection, sort_column: str) -> list[tuple]:
    """Query items table safely verifying sort column."""
    if sort_column not in ALLOWED_SORT_COLUMNS:
        sort_column = "created_at"
    query = f"SELECT id, title, created_at FROM items ORDER BY {sort_column}"
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()
