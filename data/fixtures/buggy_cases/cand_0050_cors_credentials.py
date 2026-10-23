"""Buggy Fixture: CAND-0050
Category 6: Authorization
Primary CWE: CWE-942 (Permissive Cross-origin Resource Sharing Policy with Credentials)
"""

from __future__ import annotations

def build_cors_headers(origin: str | None) -> dict[str, str]:
    """Construct CORS headers reflecting arbitrary origin with credentials."""
    return {
        "Access-Control-Allow-Origin": origin or "*",
        "Access-Control-Allow-Credentials": "true",
    }
