"""Clean Control Fixture: CTRL-0046
Paired with: CAND-0046 (Category 6: Authorization)
Target Scope: Administrative user deletion action gate
Intended Behavior: Enforces admin role privilege before deletion.
"""

from __future__ import annotations
from typing import Any

def delete_user_account(acting_user: dict[str, Any], target_user_id: str, db: dict[str, Any]) -> bool:
    """Delete user account safely validating administrative privileges."""
    if not acting_user:
        raise PermissionError("Authentication required.")
    if acting_user.get("role") != "admin":
        raise PermissionError("Administrative role required.")
    db.pop(target_user_id, None)
    return True
