"""Clean Control Fixture: CTRL-0043
Paired with: CAND-0043 (Category 5: Authentication)
Target Scope: User password hashing mechanism
Intended Behavior: Hashes password using PBKDF2-HMAC-SHA256 with 600,000 iterations.
"""

from __future__ import annotations
import hashlib
import os

def hash_user_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Compute salted PBKDF2 password digest."""
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return digest.hex(), salt.hex()
