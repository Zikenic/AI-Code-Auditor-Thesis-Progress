import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pytest
from key_vault import EphemeralSigningKeyVault
from token_signer import issue_signed_session_token, verify_signed_session_token


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
    tampered = f"{payload_b64}x.{sig}"
    with pytest.raises(Exception):
        verify_signed_session_token(tampered, vault)
