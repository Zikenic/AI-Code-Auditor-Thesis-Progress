"""Clean Control Fixture: CTRL-0050
Paired with: CAND-0050 (Category 6: Authorization)
Target Scope: CORS response headers origin verification
Intended Behavior: Whitelists allowed origins before enabling credentials.
"""

from __future__ import annotations

TRUSTED_ORIGINS = {"https://app.thesis.example.com", "https://admin.thesis.example.com"}

def build_cors_headers(origin: str | None) -> dict[str, str]:
    """Construct CORS headers safely validating against origin whitelist."""
    if origin and origin in TRUSTED_ORIGINS:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {
        "Access-Control-Allow-Origin": "null",
        "Access-Control-Allow-Credentials": "false",
    }
