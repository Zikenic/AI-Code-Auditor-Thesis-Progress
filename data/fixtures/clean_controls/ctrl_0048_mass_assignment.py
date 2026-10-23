"""Clean Control Fixture: CTRL-0048
Paired with: CAND-0048 (Category 6: Authorization)
Target Scope: User profile attribute update filtering
Intended Behavior: Whitelists only non-sensitive attributes for modification.
"""

from __future__ import annotations
from typing import Any

ALLOWED_PROFILE_FIELDS = {"display_name", "bio", "avatar_url"}

def update_user_profile(user_record: dict[str, Any], incoming_data: dict[str, Any]) -> dict[str, Any]:
    """Update profile safely restricting to whitelisted fields."""
    for field in ALLOWED_PROFILE_FIELDS:
        if field in incoming_data:
            user_record[field] = incoming_data[field]
    return user_record
