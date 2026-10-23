"""Buggy Fixture: CAND-0047
Category 6: Authorization
Primary CWE: CWE-863 (Incorrect Authorization / Multi-Tenant BOLA)
"""

from __future__ import annotations
from typing import Any

def update_tenant_setting(user_token_tenant: str, client_header_tenant: str, key: str, value: Any, db: dict[str, Any]) -> None:
    """Update setting using tenant ID supplied in client header."""
    effective_tenant = client_header_tenant or user_token_tenant
    db[f"{effective_tenant}:{key}"] = value
