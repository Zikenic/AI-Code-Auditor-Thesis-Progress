"""Clean Control Fixture: CTRL-0008
Paired with: CAND-0017 (Category 3: Database & SQL Injection)
Target Scope: Database cursor execution wrapper with parameter binding
Intended Behavior: Executes queries via DB-API parameter tuples, preventing
SQL Injection (CWE-89) in database backend adapters.
"""

from __future__ import annotations

from typing import Any, Protocol


class DbCursor(Protocol):
    """Protocol for DB-API 2.0 cursor interface."""

    def execute(self, operation: str, parameters: tuple[Any, ...] | None = None) -> Any: ...
    def fetchall(self) -> list[tuple[Any, ...]]: ...


def execute_filtered_query(cursor: DbCursor, status: str, min_priority: int) -> list[tuple[Any, ...]]:
    """Execute parameterized query using standard DB-API cursor parameter binding."""
    stmt = "SELECT task_id, title, status FROM tasks WHERE status = %s AND priority >= %s"
    cursor.execute(stmt, (status, min_priority))
    return cursor.fetchall()
