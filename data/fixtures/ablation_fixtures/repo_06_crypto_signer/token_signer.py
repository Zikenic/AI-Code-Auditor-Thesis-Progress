"""Cryptographic session token generator."""

from __future__ import annotations

import hmac
import hashlib
import json
import base64
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
    """Verify session token signature using active vault key."""
    if "." not in token:
        raise ValueError("Malformed token format")

    payload_b64, signature = token.split(".", 1)
    key = vault.get_signing_key()
    payload_bytes = base64.urlsafe_b64decode(payload_b64.encode("ascii"))

    expected_sig = hmac.new(key, payload_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        raise PermissionError("Invalid session token signature")

    return json.loads(payload_bytes.decode("utf-8"))
