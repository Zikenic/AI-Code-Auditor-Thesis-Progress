"""Clean Control Fixture: CTRL-0004
Paired with: CAND-0007 (Category 2: Input Validation / CSRF)
Target Scope: Request form validation with constant-time CSRF token verification
Intended Behavior: Validates form submission with constant-time HMAC token comparison,
preventing CSRF (CWE-352) and timing attacks.
"""

from __future__ import annotations

import hmac
import re


def validate_username(username: str) -> bool:
    """Validate that username consists strictly of alphanumeric characters and underscores."""
    if not isinstance(username, str) or len(username) < 3 or len(username) > 32:
        return False
    return bool(re.match(r"^[a-zA-Z0-9_]+$", username))


def verify_csrf_token(submitted_token: str, session_token: str) -> bool:
    """Compare CSRF tokens using constant-time comparison to prevent timing leaks."""
    if not submitted_token or not session_token:
        return False
    return hmac.compare_digest(submitted_token.encode("utf-8"), session_token.encode("utf-8"))
