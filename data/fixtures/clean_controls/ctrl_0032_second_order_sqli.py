"""Clean Control Fixture: CTRL-0032
Paired with: CAND-0029 (Category 3: SQL / ORM Injection)
Target Scope: Report generation from stored user preference
Intended Behavior: Binds stored filter parameters safely.
"""

from __future__ import annotations
import sqlite3

def generate_report_from_profile(conn: sqlite3.Connection, stored_department_filter: str) -> list[tuple]:
    """Execute reporting query safely with parameterized placeholder."""
    sql = "SELECT employee_name, salary FROM payroll WHERE department = ?"
    cur = conn.cursor()
    cur.execute(sql, (stored_department_filter,))
    return cur.fetchall()
