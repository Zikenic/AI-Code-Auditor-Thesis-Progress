"""Buggy Fixture: CAND-0037
Category 4: Path Traversal / Unsafe File Operations
Primary CWE: CWE-59 (Improper Link Resolution Before File Access)
"""

from __future__ import annotations
import os

SANDBOX_DIR = "/opt/sandbox"

def get_config_content(relative_name: str) -> str:
    """Retrieve config file content without checking symlink destination."""
    target = os.path.join(SANDBOX_DIR, relative_name)
    with open(target, "r", encoding="utf-8") as f:
        return f.read()
