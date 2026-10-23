"""Buggy Fixture: CAND-0044
Category 5: Authentication
Primary CWE: CWE-384 (Session Fixation)
"""

from __future__ import annotations
from typing import Any

def authenticate_and_bind_session(session: dict[str, Any], user_id: str) -> dict[str, Any]:
    """Bind authenticated identity to existing session dictionary."""
    session["user_id"] = user_id
    session["is_authenticated"] = True
    return session
