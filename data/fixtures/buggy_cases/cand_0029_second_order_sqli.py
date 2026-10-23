"""Buggy Fixture: CAND-0029
Category 3: SQL / ORM Injection
Primary CWE: CWE-89 (Second-Order SQL Injection)
"""

from __future__ import annotations
import sqlite3

def generate_report_from_profile(conn: sqlite3.Connection, stored_department_filter: str) -> list[tuple]:
    """Execute reporting query incorporating stored department preference."""
    sql = f"SELECT employee_name, salary FROM payroll WHERE department = '{stored_department_filter}'"
    cur = conn.cursor()
    cur.execute(sql)
    return cur.fetchall()
