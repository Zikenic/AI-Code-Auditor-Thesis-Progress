"""Buggy Fixture: CAND-0034
Category 3: SQL / ORM Injection
Primary CWE: CWE-89 (Blind SQL Injection)
"""

from __future__ import annotations
import sqlite3

def count_tenant_actions(conn: sqlite3.Connection, tenant_id: str, action: str) -> int:
    """Count audit log entries for specific tenant action."""
    query = f"SELECT count(*) FROM audit_logs WHERE tenant_id = '{tenant_id}' AND action = '{action}'"
    cur = conn.cursor()
    cur.execute(query)
    row = cur.fetchone()
    return row[0] if row else 0
