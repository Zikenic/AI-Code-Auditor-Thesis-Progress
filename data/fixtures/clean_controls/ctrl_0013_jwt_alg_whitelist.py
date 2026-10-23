"""Clean Control Fixture: CTRL-0013
Paired with: CAND-0025 (Category 5: Authentication & Cryptographic Misuse)
Target Scope: JWT algorithm whitelist validation and signature checking
Intended Behavior: Enforces an explicit whitelist of allowed algorithms and verifies
signatures using constant-time comparison, preventing algorithm confusion (CWE-347).
"""

from __future__ import annotations

import hashlib
import hmac

ALLOWED_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})


def verify_hmac_jwt_signature(
    header_alg: str,
    signing_input: bytes,
    signature: bytes,
    secret_key: bytes,
) -> bool:
    """Verify HMAC signature against declared header algorithm with strict whitelist."""
    if header_alg not in ALLOWED_ALGORITHMS:
        # Explicitly reject 'none' or asymmetric algs with symmetric key
        return False

    digest_mod = {
        "HS256": hashlib.sha256,
        "HS384": hashlib.sha384,
        "HS512": hashlib.sha512,
    }[header_alg]

    expected = hmac.new(secret_key, signing_input, digestmod=digest_mod).digest()
    return hmac.compare_digest(expected, signature)
