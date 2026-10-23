"""Clean Control Fixture: CTRL-0025
Paired with: CAND-0013 (Category 2: Input Validation / Sanitization)
Target Scope: Authentication redirect target URL validation
Intended Behavior: Rejects protocol-relative URLs (//) and external hosts.
"""

from __future__ import annotations
import urllib.parse

def get_redirect_target(next_url: str | None, default: str = "/dashboard") -> str:
    """Determine redirect target safely preventing open redirect."""
    if not next_url:
        return default
    # Disallow protocol-relative URLs like //attacker.com
    if next_url.startswith("//") or next_url.startswith("/\\"):
        return default
    parsed = urllib.parse.urlparse(next_url)
    if not parsed.netloc and next_url.startswith("/"):
        return next_url
    return default
