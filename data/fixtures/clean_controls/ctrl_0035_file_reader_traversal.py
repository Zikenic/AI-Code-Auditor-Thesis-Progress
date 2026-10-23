"""Clean Control Fixture: CTRL-0035
Paired with: CAND-0035 (Category 4: Path Traversal / Unsafe File Operations)
Target Scope: Document repository file content extraction
Intended Behavior: Validates canonical path confinement within STORAGE_DIR.
"""

from __future__ import annotations
from pathlib import Path

STORAGE_DIR = Path("/var/data/uploads").resolve()

def read_user_document(user_filename: str) -> str:
    """Read document safely verifying sandbox boundary."""
    safe_path = (STORAGE_DIR / user_filename).resolve()
    if not safe_path.is_relative_to(STORAGE_DIR):
        raise PermissionError("Access denied: path traversal detected.")
    with open(safe_path, "r", encoding="utf-8") as f:
        return f.read()
