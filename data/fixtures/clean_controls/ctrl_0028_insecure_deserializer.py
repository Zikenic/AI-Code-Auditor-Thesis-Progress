"""Clean Control Fixture: CTRL-0028
Paired with: CAND-0022 (Category 2: Input Validation / Sanitization)
Target Scope: Session cookie data deserialization
Intended Behavior: Uses secure JSON parsing instead of unsafe pickle.
"""

from __future__ import annotations
import base64
import json
from typing import Any

def unpack_session_token(token_str: str) -> dict[str, Any]:
    """Extract session dictionary safely using JSON deserialization."""
    raw_bytes = base64.b64decode(token_str)
    return json.loads(raw_bytes.decode("utf-8"))
