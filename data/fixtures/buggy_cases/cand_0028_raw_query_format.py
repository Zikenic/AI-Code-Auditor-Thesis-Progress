"""Buggy Fixture: CAND-0028
Category 3: SQL / ORM Injection
Primary CWE: CWE-89 (SQL Injection)
"""

from __future__ import annotations
import sqlite3

def find_user_by_email(conn: sqlite3.Connection, email: str) -> tuple | None:
    """Find user record by email address."""
    query = f"SELECT id, email, role FROM users WHERE email = '{email}'"
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchone()
