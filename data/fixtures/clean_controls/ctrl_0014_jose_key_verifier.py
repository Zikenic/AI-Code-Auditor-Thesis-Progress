"""Clean Control Fixture: CTRL-0014
Paired with: CAND-0027 (Category 5: Authentication & Cryptographic Misuse)
Target Scope: Cryptographic key structure and parameter validation for JOSE
Intended Behavior: Validates cryptographic key type and curve parameters explicitly
before invoking verification routines, avoiding invalid curve attacks (CWE-347).
"""

from __future__ import annotations

from typing import Any

VALID_OCT_MIN_BITS = 256
VALID_RSA_MIN_BITS = 2048


def validate_key_parameters(key_type: str, key_data: dict[str, Any]) -> bool:
    """Validate cryptographic key metadata before use in signature verification."""
    kty = key_type.upper()
    if kty == "OCT":
        # Symmetric key must meet minimum length
        secret_bytes = key_data.get("k", b"")
        if isinstance(secret_bytes, str):
            secret_bytes = secret_bytes.encode("utf-8")
        return len(secret_bytes) * 8 >= VALID_OCT_MIN_BITS

    if kty == "RSA":
        bit_length = int(key_data.get("bit_length", 0))
        return bit_length >= VALID_RSA_MIN_BITS

    return False
