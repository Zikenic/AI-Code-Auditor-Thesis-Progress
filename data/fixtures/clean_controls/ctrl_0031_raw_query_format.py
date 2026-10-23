"""Clean Control Fixture: CTRL-0031
Paired with: CAND-0028 (Category 3: SQL / ORM Injection)
Target Scope: User lookup query construction
Intended Behavior: Uses parameter placeholders preventing query interpolation.
"""

from __future__ import annotations
import sqlite3

def find_user_by_email(conn: sqlite3.Connection, email: str) -> tuple | None:
    """Find user record safely using parameterized binding."""
    query = "SELECT id, email, role FROM users WHERE email = ?"
    cursor = conn.cursor()
    cursor.execute(query, (email,))
    return cursor.fetchone()
