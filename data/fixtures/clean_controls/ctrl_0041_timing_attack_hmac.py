"""Clean Control Fixture: CTRL-0041
Paired with: CAND-0041 (Category 5: Authentication)
Target Scope: API webhook HMAC signature verification
Intended Behavior: Employs hmac.compare_digest for constant-time evaluation.
"""

from __future__ import annotations
import hashlib
import hmac

def verify_payload_signature(secret: str, payload: bytes, provided_sig: str) -> bool:
    """Verify webhook payload signature using constant-time digest comparison."""
    expected_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_sig, provided_sig)
