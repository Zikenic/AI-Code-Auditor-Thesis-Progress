import hashlib
import sys
from pathlib import Path

for mod in ["login_handler", "rate_limiter"]:
    if mod in sys.modules:
        del sys.modules[mod]

sys.path.insert(0, str(Path(__file__).parent))

import pytest  # noqa: E402
from login_handler import (  # noqa: E402
    MIN_SALT_BYTES,
    check_needs_rehash,
    create_credential_record,
    generate_salt,
    import_legacy_credential_record,
    process_login_attempt,
    validate_salt,
    verify_credential_record,
)
from rate_limiter import RateLimitExceeded, SlidingWindowRateLimiter  # noqa: E402


def test_generate_salt_byte_controls_and_entropy():
    # Default is 16 bytes = 32 hex chars
    default_salt = generate_salt()
    assert isinstance(default_salt, str)
    assert len(default_salt) == MIN_SALT_BYTES * 2 == 32

    # num_bytes controls length explicitly
    salt_4 = generate_salt(num_bytes=4)
    assert len(salt_4) == 8  # 4 bytes = 8 hex chars = 32 bits minimum

    salt_32 = generate_salt(num_bytes=32)
    assert len(salt_32) == 64  # 32 bytes = 64 hex chars = 256 bits

    # Freshness across consecutive calls
    salt_a = generate_salt(16)
    salt_b = generate_salt(16)
    assert salt_a != salt_b

    # Rejection of invalid byte counts (< 4 bytes)
    with pytest.raises(ValueError, match="at least 4 bytes"):
        generate_salt(num_bytes=3)

    with pytest.raises(ValueError, match="at least 4 bytes"):
        generate_salt(num_bytes="16")  # type: ignore[arg-type]


def test_validate_salt_contract():
    # Valid salts
    validate_salt("01234567")  # 8 hex chars = 4 bytes
    validate_salt("abcdef0123456789")  # 16 hex chars
    validate_salt("a" * 32)  # 32 hex chars

    # Non-string values
    with pytest.raises(ValueError, match="Salt must be a string"):
        validate_salt(12345678)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Salt must be a string"):
        validate_salt(None)  # type: ignore[arg-type]

    # Empty string
    with pytest.raises(ValueError, match="at least 8 characters"):
        validate_salt("")

    # Less than 8 characters (32 bits)
    with pytest.raises(ValueError, match="at least 8 characters"):
        validate_salt("123456")  # 6 chars

    # Odd length string
    with pytest.raises(ValueError, match="even length"):
        validate_salt("123456789")  # 9 chars

    # Non-hexadecimal characters
    with pytest.raises(ValueError, match="valid hexadecimal characters"):
        validate_salt("zzzzzzzz")

    with pytest.raises(ValueError, match="valid hexadecimal characters"):
        validate_salt("random_salt_test")

    with pytest.raises(ValueError, match="valid hexadecimal characters"):
        validate_salt("        ")  # whitespace


def test_create_credential_record_generates_fresh_salt():
    rec1 = create_credential_record("my_secret_pass", iterations=10_000)
    rec2 = create_credential_record("my_secret_pass", iterations=10_000)

    assert rec1["scheme"] == "pbkdf2_hmac_sha256"
    assert rec1["iterations"] == 10_000
    assert len(rec1["salt"]) == 32
    assert isinstance(rec1["hash"], str)
    assert len(rec1["hash"]) == 64

    # Fresh salt generated each time even with identical password
    assert rec1["salt"] != rec2["salt"]
    assert rec1["hash"] != rec2["hash"]


def test_create_credential_record_oversized_rejected():
    huge_pw = "P" * 5000
    with pytest.raises(ValueError, match="Password must be a string up to 4096 characters"):
        create_credential_record(huge_pw)


def test_import_legacy_credential_record():
    salt = generate_salt(16)
    rec = import_legacy_credential_record("legacy_pass", salt, iterations=50_000)
    assert rec["salt"] == salt
    assert rec["iterations"] == 50_000
    assert rec["scheme"] == "pbkdf2_hmac_sha256"

    # Rejects malformed salt
    with pytest.raises(ValueError, match="valid hexadecimal characters"):
        import_legacy_credential_record("legacy_pass", "invalid_salt_!00")


def test_verify_credential_record_success_and_failure():
    limiter = SlidingWindowRateLimiter(max_attempts=5, window_seconds=60)
    rec = create_credential_record("correct_horse_battery", iterations=10_000)

    # Verification succeeds with matching password
    assert verify_credential_record(rec, "correct_horse_battery", limiter, username="alice") is True

    # Verification fails with wrong password
    assert verify_credential_record(rec, "wrong_horse_battery", limiter, username="alice") is False


def test_verify_credential_record_uses_stored_iterations():
    limiter = SlidingWindowRateLimiter(max_attempts=5, window_seconds=60)
    # Record stored with non-default iteration count
    rec = create_credential_record("my_pw", iterations=25_000)

    # Verification uses record's 25_000 iterations, not DEFAULT_PBKDF2_ITERATIONS (600_000)
    assert verify_credential_record(rec, "my_pw", limiter, username="bob") is True


def test_verify_credential_record_rejects_unsupported_scheme():
    limiter = SlidingWindowRateLimiter(max_attempts=5, window_seconds=60)
    bad_rec = {
        "scheme": "md5_insecure",
        "iterations": 1000,
        "salt": generate_salt(16),
        "hash": "somehash",
    }
    with pytest.raises(ValueError, match="Unsupported credential scheme"):
        verify_credential_record(bad_rec, "pw", limiter)


def test_check_needs_rehash():
    old_rec = {"scheme": "pbkdf2_hmac_sha256", "iterations": 100_000}
    assert check_needs_rehash(old_rec, target_iterations=600_000) is True

    current_rec = {"scheme": "pbkdf2_hmac_sha256", "iterations": 600_000}
    assert check_needs_rehash(current_rec, target_iterations=600_000) is False

    different_scheme = {"scheme": "argon2id", "iterations": 600_000}
    assert check_needs_rehash(different_scheme, target_scheme="pbkdf2_hmac_sha256") is True


def test_process_login_attempt_raw_api():
    limiter = SlidingWindowRateLimiter(max_attempts=3, window_seconds=60)
    salt = generate_salt(16)
    stored = hashlib.pbkdf2_hmac("sha256", b"secret123", salt.encode("utf-8"), 10_000).hex()

    # Success
    assert process_login_attempt("alice", "secret123", stored, salt, limiter, iterations=10_000) is True

    # Failure
    assert process_login_attempt("alice", "wrong_pass", stored, salt, limiter, iterations=10_000) is False


def test_process_login_attempt_rate_limited():
    limiter = SlidingWindowRateLimiter(max_attempts=2, window_seconds=60)
    salt = generate_salt(16)
    stored = "wrong_hash"

    process_login_attempt("carol", "wrong1", stored, salt, limiter, iterations=10_000)
    process_login_attempt("carol", "wrong2", stored, salt, limiter, iterations=10_000)

    with pytest.raises(RateLimitExceeded):
        process_login_attempt("carol", "wrong3", stored, salt, limiter, iterations=10_000)


def test_process_login_attempt_input_bounds():
    limiter = SlidingWindowRateLimiter(max_attempts=5, window_seconds=60)
    salt = generate_salt(16)
    huge_pw = "A" * 5000
    huge_user = "U" * 300

    with pytest.raises(ValueError, match="Password attempt must be a string up to 4096 characters"):
        process_login_attempt("dave", huge_pw, "hash", salt, limiter)

    with pytest.raises(ValueError, match="Username must be a string up to 256 characters"):
        process_login_attempt(huge_user, "valid_pass", "hash", salt, limiter)
