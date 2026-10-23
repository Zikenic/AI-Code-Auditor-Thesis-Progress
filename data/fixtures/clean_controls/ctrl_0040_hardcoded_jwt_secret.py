"""Clean Control Fixture: CTRL-0040
Paired with: CAND-0040 (Category 5: Authentication)
Target Scope: JWT signing secret key configuration
Intended Behavior: Mandatory retrieval from environment variable without fallback.
"""

from __future__ import annotations
import os

def get_signing_secret() -> str:
    """Retrieve secret key safely from environment."""
    secret = os.environ.get("JWT_SECRET_KEY")
    if not secret or len(secret) < 32:
        raise ValueError("JWT_SECRET_KEY must be configured with >=32 chars.")
    return secret
