"""Clean Control Fixture: CTRL-0015
Paired with: CAND-0026 (Category 5: Authentication & Cryptographic Misuse)
Target Scope: Transport authentication handshake and credential verification
Intended Behavior: Authenticates client credentials using constant-time comparison
secrets.compare_digest, preventing timing side-channel attacks (CWE-287 / CWE-208).
"""

from __future__ import annotations

import secrets


def verify_client_handshake(provided_api_token: str, expected_system_token: str) -> bool:
    """Validate API token in constant time to eliminate timing variations."""
    if not isinstance(provided_api_token, str) or not isinstance(expected_system_token, str):
        return False

    return secrets.compare_digest(
        provided_api_token.encode("utf-8"),
        expected_system_token.encode("utf-8"),
    )
