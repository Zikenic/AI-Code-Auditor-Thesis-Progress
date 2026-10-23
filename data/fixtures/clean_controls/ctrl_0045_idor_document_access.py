"""Clean Control Fixture: CTRL-0045
Paired with: CAND-0045 (Category 6: Authorization)
Target Scope: Document record retrieval by client identifier
Intended Behavior: Verifies current user owns or is authorized for the document.
"""

from __future__ import annotations
from typing import Any

def get_document(doc_id: str, current_user_id: str, db_store: dict[str, Any]) -> dict[str, Any] | None:
    """Retrieve document safely checking user ownership."""
    doc = db_store.get(doc_id)
    if not doc:
        return None
    if doc.get("owner_id") != current_user_id:
        raise PermissionError("Access forbidden: you do not own this document.")
    return doc
