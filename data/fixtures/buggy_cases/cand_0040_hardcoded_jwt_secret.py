"""Buggy Fixture: CAND-0040
Category 5: Authentication
Primary CWE: CWE-798 (Use of Hard-coded Credentials)
"""

from __future__ import annotations

JWT_SECRET_KEY = "SUPER_SECRET_PRODUCTION_KEY_DO_NOT_DISCLOSE_12345"

def get_signing_secret() -> str:
    """Retrieve secret key for JWT verification."""
    return JWT_SECRET_KEY
