"""Clean Control Fixture: CTRL-0034
Paired with: CAND-0034 (Category 3: SQL / ORM Injection)
Target Scope: Tenant audit log record count check
Intended Behavior: Binds tenant and action parameters securely.
"""

from __future__ import annotations
import sqlite3

def count_tenant_actions(conn: sqlite3.Connection, tenant_id: str, action: str) -> int:
    """Count audit log entries safely using placeholders."""
    query = "SELECT count(*) FROM audit_logs WHERE tenant_id = ? AND action = ?"
    cur = conn.cursor()
    cur.execute(query, (tenant_id, action))
    row = cur.fetchone()
    return row[0] if row else 0
