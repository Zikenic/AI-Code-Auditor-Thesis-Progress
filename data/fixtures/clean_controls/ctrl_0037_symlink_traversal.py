"""Clean Control Fixture: CTRL-0037
Paired with: CAND-0037 (Category 4: Path Traversal / Unsafe File Operations)
Target Scope: Filesystem link resolution and traversal safety
Intended Behavior: Resolves symlinks and ensures final target resides in sandbox.
"""

from __future__ import annotations
from pathlib import Path

SANDBOX_DIR = Path("/opt/sandbox").resolve()

def get_config_content(relative_name: str) -> str:
    """Retrieve config file safely checking real symlink target."""
    target = (SANDBOX_DIR / relative_name).resolve(strict=True)
    if not target.is_relative_to(SANDBOX_DIR):
        raise PermissionError("Symlink escapes restricted sandbox.")
    with open(target, "r", encoding="utf-8") as f:
        return f.read()
