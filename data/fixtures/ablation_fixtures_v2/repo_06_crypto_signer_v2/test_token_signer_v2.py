import sys
import time
from pathlib import Path

for mod in ["token_signer", "key_vault"]:
    if mod in sys.modules:
        del sys.modules[mod]

sys.path.insert(0, str(Path(__file__).parent))

import pytest  # noqa: E402
from key_vault import EphemeralSigningKeyVault  # noqa: E402
from token_signer import issue_signed_session_token, verify_signed_session_token  # noqa: E402


def test_token_signer_roundtrip():
    vault = EphemeralSigningKeyVault()
    token = issue_signed_session_token({"sub": "user_42", "role": "admin"}, vault)
    claims = verify_signed_session_token(token, vault)
    assert claims["sub"] == "user_42"
    assert claims["role"] == "admin"


def test_token_tampering_rejected():
    vault = EphemeralSigningKeyVault()
    token = issue_signed_session_token({"sub": "user_42"}, vault)
    payload_b64, sig = token.split(".", 1)
    # Tamper signature so payload decodes cleanly but signature validation fails
    tampered_sig = ("0000" if sig[:4] != "0000" else "ffff") + sig[4:]
    tampered = f"{payload_b64}.{tampered_sig}"
    with pytest.raises(PermissionError, match="Invalid session token signature"):
        verify_signed_session_token(tampered, vault)


def test_token_malformed_padding_raises_value_error():
    vault = EphemeralSigningKeyVault()
    # Malformed base64 segment with invalid characters
    with pytest.raises(ValueError):
        verify_signed_session_token("!!invalid-base64!!.sig123", vault)


def test_token_key_rotation_grace_period():
    vault = EphemeralSigningKeyVault(key_ttl_seconds=0.1, grace_period_seconds=1.0)
    token = issue_signed_session_token({"sub": "user_rotated"}, vault)

    # Force key rotation by waiting past TTL
    time.sleep(0.15)
    _ = vault.get_signing_key()  # Triggers rotation

    # Token signed before rotation should still verify within grace period
    claims = verify_signed_session_token(token, vault)
    assert claims["sub"] == "user_rotated"
