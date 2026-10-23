import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pytest
import hashlib
from rate_limiter import SlidingWindowRateLimiter, RateLimitExceeded
from login_handler import process_login_attempt


def test_process_login_success():
    limiter = SlidingWindowRateLimiter(max_attempts=3, window_seconds=60)
    salt = "random_salt"
    stored = hashlib.pbkdf2_hmac("sha256", b"secret123", salt.encode("utf-8"), 100_000).hex()

    assert process_login_attempt("alice", "secret123", stored, salt, limiter) is True


def test_process_login_rate_limited():
    limiter = SlidingWindowRateLimiter(max_attempts=2, window_seconds=60)
    salt = "random_salt"
    stored = "wrong_hash"

    process_login_attempt("bob", "wrong1", stored, salt, limiter)
    process_login_attempt("bob", "wrong2", stored, salt, limiter)

    with pytest.raises(RateLimitExceeded):
        process_login_attempt("bob", "wrong3", stored, salt, limiter)
