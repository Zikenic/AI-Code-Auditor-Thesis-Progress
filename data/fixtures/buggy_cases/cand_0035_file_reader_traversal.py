"""Buggy Fixture: CAND-0035
Category 4: Path Traversal / Unsafe File Operations
Primary CWE: CWE-22 (Improper Limitation of a Pathname to a Restricted Directory)
"""

from __future__ import annotations
import os

STORAGE_DIR = "/var/data/uploads"

def read_user_document(user_filename: str) -> str:
    """Read document from disk given client filename."""
    full_path = os.path.join(STORAGE_DIR, user_filename)
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()
