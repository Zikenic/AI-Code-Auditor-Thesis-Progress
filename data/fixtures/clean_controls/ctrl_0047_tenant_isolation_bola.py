"""Clean Control Fixture: CTRL-0047
Paired with: CAND-0047 (Category 6: Authorization)
Target Scope: Multi-tenant resource modification authorization
Intended Behavior: Ignores client header and enforces authenticated token tenant.
"""

from __future__ import annotations
from typing import Any

def update_tenant_setting(user_token_tenant: str, client_header_tenant: str, key: str, value: Any, db: dict[str, Any]) -> None:
    """Update setting safely using token tenant."""
    effective_tenant = user_token_tenant
    db[f"{effective_tenant}:{key}"] = value
