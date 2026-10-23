"""Buggy Fixture: CAND-0012
Category 2: Input Validation / Sanitization
Primary CWE: CWE-918 (Server-Side Request Forgery - SSRF)
"""

from __future__ import annotations
import urllib.request

def fetch_webhook_payload(target_url: str) -> str:
    """Fetch webhook body from remote endpoint."""
    req = urllib.request.Request(target_url)
    with urllib.request.urlopen(req, timeout=5) as response:
        return response.read().decode("utf-8")
