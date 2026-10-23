"""Cryptographic session token generator with rotation tolerance and safe decoding (v2)."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from typing import Any

from key_vault import EphemeralSigningKeyVault


def issue_signed_session_token(claims: dict[str, Any], vault: EphemeralSigningKeyVault) -> str:
    """Issue a cryptographically signed HMAC-SHA256 session token.

    Delegates key management to `key_vault.EphemeralSigningKeyVault` to ensure
    keys are rotated CSPRNG-derived secrets rather than static or hardcoded keys.
    """
    key = vault.get_signing_key()
    payload_bytes = json.dumps(claims, sort_keys=True).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("ascii")

    signature = hmac.new(key, payload_bytes, hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


def verify_signed_session_token(token: str, vault: EphemeralSigningKeyVault) -> dict[str, Any]:
    """Verify session token signature using active or grace-period vault keys."""
    if "." not in token:
        raise ValueError("Malformed token format: missing signature delimiter")

    payload_b64, signature = token.split(".", 1)

    # Safely decode base64 payload handling padding and corrupt input cleanly
    try:
        # Add required padding if stripped and normalize URL-safe characters
        padded_b64 = payload_b64 + "=" * (-len(payload_b64) % 4)
        std_b64 = padded_b64.replace("-", "+").replace("_", "/")
        payload_bytes = base64.b64decode(std_b64.encode("ascii"), validate=True)
    except (binascii.Error, ValueError) as err:
        raise ValueError(f"Malformed token payload encoding: {err}") from err

    # Check against active key and valid grace-period rotated keys
    valid = False
    for candidate_key in vault.get_verification_keys():
        expected_sig = hmac.new(candidate_key, payload_bytes, hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected_sig):
            valid = True
            break

    if not valid:
        raise PermissionError("Invalid session token signature")

    try:
        claims = json.loads(payload_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as err:
        raise ValueError(f"Invalid token JSON claims: {err}") from err

    return claims
