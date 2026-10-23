"""Buggy Fixture: CAND-0042
Category 5: Authentication
Primary CWE: CWE-613 (Insufficient Session Expiration)
"""

from __future__ import annotations
from typing import Any

def validate_claims(claims: dict[str, Any]) -> bool:
    """Validate token payload claims."""
    # Only verify presence of user identifier, ignoring exp timestamp
    return "sub" in claims
