"""Buggy Fixture: CAND-0049
Category 6: Authorization
Primary CWE: CWE-862 (Missing Authorization in Password Reset)
"""

from __future__ import annotations
from typing import Any

def apply_password_reset(token: str, target_user_id: str, new_password_hash: str, token_store: dict[str, Any], user_store: dict[str, Any]) -> bool:
    """Reset password without binding token to specific user."""
    if token in token_store:
        user_store[target_user_id]["password_hash"] = new_password_hash
        token_store.pop(token)
        return True
    return False
