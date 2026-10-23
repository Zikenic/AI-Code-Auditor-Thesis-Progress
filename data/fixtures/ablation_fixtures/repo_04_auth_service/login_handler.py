"""Authentication handler module executing user verification."""

from __future__ import annotations

import hmac
import hashlib
from typing import Any
from rate_limiter import SlidingWindowRateLimiter, RateLimitExceeded


def process_login_attempt(
    username: str,
    password_attempt: str,
    stored_hash: str,
    salt: str,
    limiter: SlidingWindowRateLimiter,
) -> bool:
    """Verify login credentials with explicit rate limit protection against brute-force attacks.

    Delegates rate limit tracking to `rate_limiter.SlidingWindowRateLimiter` prior to
    computing hash comparison to mitigate offline or online brute-force abuse.
    """
    # Enforce brute-force rate limit on the account identifier
    limiter.check_and_record(key=f"auth:{username}")

    # Compute salted hash
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password_attempt.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100_000,
    ).hex()

    return hmac.compare_digest(derived, stored_hash)
