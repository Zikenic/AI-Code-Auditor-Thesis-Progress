"""Clean Control Fixture: CTRL-0010
Paired with: CAND-0019 (Category 4: Path Traversal / File Access)
Target Scope: Static file dispatcher path resolution
Intended Behavior: Resolves file path and verifies containment inside base directory
using pathlib.Path.is_relative_to, preventing Path Traversal (CWE-22).
"""

from __future__ import annotations

from pathlib import Path


def resolve_safe_static_path(base_dir: Path, requested_subpath: str) -> Path | None:
    """Resolve and sanitize static asset path, rejecting directory traversal attempts."""
    # Strip leading slash or backslash
    clean_subpath = requested_subpath.lstrip("/\\")
    target = (base_dir / clean_subpath).resolve()

    try:
        # Check containment within declared base directory
        if not target.is_relative_to(base_dir.resolve()):
            return None
    except (ValueError, AttributeError):
        return None

    if target.is_file():
        return target
    return None
