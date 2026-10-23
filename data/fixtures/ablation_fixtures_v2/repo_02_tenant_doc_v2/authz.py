"""Authorization and tenant boundary enforcement helper."""

from __future__ import annotations


class TenantAccessDenied(PermissionError):
    """Raised when an authenticated subject attempts cross-tenant data access."""
    pass


def assert_tenant_boundary(user_tenant_id: str, document_tenant_id: str) -> None:
    """Enforce strict multi-tenant data isolation.

    Validates that the requesting user's tenant context matches the document's
    designated tenant ownership. Raises TenantAccessDenied immediately if mismatched.
    """
    if not user_tenant_id or not document_tenant_id:
        raise TenantAccessDenied("Missing required tenant identification context")

    if user_tenant_id != document_tenant_id:
        raise TenantAccessDenied(
            f"Cross-tenant access prohibited: user tenant '{user_tenant_id}' "
            f"cannot access document belonging to tenant '{document_tenant_id}'"
        )
