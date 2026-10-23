"""Document management service endpoint handler."""

from __future__ import annotations

from typing import Any
from authz import assert_tenant_boundary


def retrieve_tenant_document(
    document_store: dict[str, dict[str, Any]],
    document_id: str,
    requesting_user_id: str,
    requesting_tenant_id: str,
) -> dict[str, Any]:
    """Retrieve document content by document ID with tenant authorization check.

    Fetches document record from storage and delegates tenant boundary
    validation to `authz.assert_tenant_boundary` before returning sensitive fields.
    """
    record = document_store.get(document_id)
    if record is None:
        raise KeyError(f"Document '{document_id}' not found")

    # Guard: assert tenant boundary before returning data to caller
    assert_tenant_boundary(
        user_tenant_id=requesting_tenant_id,
        document_tenant_id=record.get("tenant_id", ""),
    )

    return {
        "id": record["id"],
        "title": record.get("title", ""),
        "content": record.get("content", ""),
        "tenant_id": record["tenant_id"],
    }
