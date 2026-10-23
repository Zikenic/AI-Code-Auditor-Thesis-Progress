"""Buggy Fixture: CAND-0043
Category 5: Authentication
Primary CWE: CWE-327 (Use of a Broken or Risky Cryptographic Algorithm)
"""

from __future__ import annotations
import hashlib

def hash_user_password(password: str) -> str:
    """Compute digest of password using legacy algorithm."""
    return hashlib.md5(password.encode("utf-8")).hexdigest()
