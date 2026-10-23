"""Clean Control Fixture: CTRL-0049
Paired with: CAND-0049 (Category 6: Authorization)
Target Scope: Password reset token identity binding check
Intended Behavior: Validates token identity matches target_user_id strictly.
"""

from __future__ import annotations
from typing import Any

def apply_password_reset(token: str, target_user_id: str, new_password_hash: str, token_store: dict[str, Any], user_store: dict[str, Any]) -> bool:
    """Reset password safely verifying token user binding."""
    token_data = token_store.get(token)
    if not token_data or token_data.get("bound_user_id") != target_user_id:
        return False
    user_store[target_user_id]["password_hash"] = new_password_hash
    token_store.pop(token, None)
    return True
