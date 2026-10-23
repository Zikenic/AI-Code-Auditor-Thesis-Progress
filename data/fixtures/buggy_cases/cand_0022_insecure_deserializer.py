"""Buggy Fixture: CAND-0022
Category 2: Input Validation / Sanitization
Primary CWE: CWE-502 (Deserialization of Untrusted Data)
"""

from __future__ import annotations
import base64
import pickle
from typing import Any

def unpack_session_token(token_str: str) -> dict[str, Any]:
    """Extract session dictionary from base64 token."""
    raw_bytes = base64.b64decode(token_str)
    return pickle.loads(raw_bytes)
