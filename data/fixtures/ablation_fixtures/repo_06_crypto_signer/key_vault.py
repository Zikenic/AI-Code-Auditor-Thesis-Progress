"""Key vault client providing rotated, cryptographically secure signing keys."""

from __future__ import annotations

import secrets
import time


class EphemeralSigningKeyVault:
    """Manages secure HMAC signing keys with automatic generation and rotation."""

    def __init__(self, key_ttl_seconds: float = 3600.0):
        self.key_ttl_seconds = key_ttl_seconds
        self._current_key: bytes | None = None
        self._key_generated_at: float = 0.0

    def get_signing_key(self) -> bytes:
        """Retrieve the active 256-bit cryptographically secure signing key.

        Rotates automatically if the key lifetime exceeds `key_ttl_seconds`.
        Guarantees high-entropy CSPRNG source via `secrets.token_bytes(32)`.
        """
        now = time.monotonic()
        if self._current_key is None or (now - self._key_generated_at) > self.key_ttl_seconds:
            # Generate fresh 256-bit CSPRNG key
            self._current_key = secrets.token_bytes(32)
            self._key_generated_at = now

        return self._current_key
