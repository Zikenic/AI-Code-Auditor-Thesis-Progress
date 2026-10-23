"""Clean Control Fixture: CTRL-0042
Paired with: CAND-0042 (Category 5: Authentication)
Target Scope: Authentication token validity claim verification
Intended Behavior: Validates token expiration timestamp strictly.
"""

from __future__ import annotations
import time
from typing import Any

def validate_claims(claims: dict[str, Any]) -> bool:
    """Validate token payload claims verifying strict expiration."""
    if "sub" not in claims or "exp" not in claims:
        return False
    now = int(time.time())
    return claims["exp"] > now
