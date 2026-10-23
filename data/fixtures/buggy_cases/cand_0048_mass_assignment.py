"""Buggy Fixture: CAND-0048
Category 6: Authorization
Primary CWE: CWE-915 (Improperly Controlled Modification of Dynamically-Determined Object Attributes)
"""

from __future__ import annotations
from typing import Any

def update_user_profile(user_record: dict[str, Any], incoming_data: dict[str, Any]) -> dict[str, Any]:
    """Update profile attributes directly from incoming request."""
    user_record.update(incoming_data)
    return user_record
