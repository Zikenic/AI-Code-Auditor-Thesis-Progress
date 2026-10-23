"""Buggy Fixture: CAND-0046
Category 6: Authorization
Primary CWE: CWE-862 (Missing Authorization)
"""

from __future__ import annotations
from typing import Any

def delete_user_account(acting_user: dict[str, Any], target_user_id: str, db: dict[str, Any]) -> bool:
    """Delete user account checking only authentication presence."""
    if not acting_user:
        raise PermissionError("Authentication required.")
    db.pop(target_user_id, None)
    return True
