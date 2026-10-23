"""Buggy Fixture: CAND-0041
Category 5: Authentication
Primary CWE: CWE-208 (Observable Timing Discrepancy)
"""

from __future__ import annotations
import hashlib
import hmac

def verify_payload_signature(secret: str, payload: bytes, provided_sig: str) -> bool:
    """Verify webhook payload signature using standard equality."""
    expected_sig = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return expected_sig == provided_sig
