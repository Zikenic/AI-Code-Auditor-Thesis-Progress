"""Buggy Fixture: CAND-0045
Category 6: Authorization
Primary CWE: CWE-639 (Authorization Bypass Through User-Controlled Key / IDOR)
"""

from __future__ import annotations
from typing import Any

def get_document(doc_id: str, current_user_id: str, db_store: dict[str, Any]) -> dict[str, Any] | None:
    """Retrieve document by ID without verifying owner."""
    return db_store.get(doc_id)
