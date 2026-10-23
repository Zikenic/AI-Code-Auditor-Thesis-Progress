"""Key vault client providing rotated keys with verification grace period (v2)."""

from __future__ import annotations

import secrets
import time


class EphemeralSigningKeyVault:
    """Manages secure HMAC signing keys with automatic generation, rotation, and grace periods."""

    def __init__(self, key_ttl_seconds: float = 3600.0, grace_period_seconds: float = 1800.0):
        self.key_ttl_seconds = key_ttl_seconds
        self.grace_period_seconds = grace_period_seconds
        self._current_key: bytes | None = None
        self._key_generated_at: float = 0.0
        self._previous_keys: list[tuple[bytes, float]] = []

    def get_signing_key(self) -> bytes:
        """Retrieve the active 256-bit cryptographically secure signing key.

        Rotates automatically if the key lifetime exceeds `key_ttl_seconds`.
        Preserves previous keys within `grace_period_seconds` for session continuity.
        """
        now = time.monotonic()
        if self._current_key is None or (now - self._key_generated_at) > self.key_ttl_seconds:
            if self._current_key is not None:
                self._previous_keys.append((self._current_key, self._key_generated_at))
            # Generate fresh 256-bit CSPRNG key
            self._current_key = secrets.token_bytes(32)
            self._key_generated_at = now

        # Prune expired keys outside grace period
        cutoff = now - (self.key_ttl_seconds + self.grace_period_seconds)
        self._previous_keys = [k for k in self._previous_keys if k[1] > cutoff]

        return self._current_key

    def get_verification_keys(self) -> list[bytes]:
        """Retrieve all currently valid keys for verification (current key + valid previous keys)."""
        active_key = self.get_signing_key()
        keys = [active_key]
        now = time.monotonic()
        cutoff = now - (self.key_ttl_seconds + self.grace_period_seconds)
        for k, gen_time in reversed(self._previous_keys):
            if gen_time > cutoff and k not in keys:
                keys.append(k)
        return keys
