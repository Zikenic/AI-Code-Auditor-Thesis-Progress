"""Buggy Fixture: CAND-0024
Category 3: SQL / ORM Injection
Primary CWE: CWE-89 (SQL Injection)
"""

from __future__ import annotations
import sqlite3

def get_sorted_records(conn: sqlite3.Connection, sort_column: str) -> list[tuple]:
    """Query items table ordered by user-supplied column."""
    query = f"SELECT id, title, created_at FROM items ORDER BY {sort_column}"
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()
