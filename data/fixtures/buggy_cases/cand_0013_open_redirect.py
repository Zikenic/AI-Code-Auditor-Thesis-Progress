"""Buggy Fixture: CAND-0013
Category 2: Input Validation / Sanitization
Primary CWE: CWE-601 (URL Redirection to Untrusted Site)
"""

from __future__ import annotations

def get_redirect_target(next_url: str | None, default: str = "/dashboard") -> str:
    """Determine redirect target after successful login."""
    if next_url and next_url.startswith("/"):
        return next_url
    return default
