"""Clean Control Fixture: CTRL-0011
Paired with: CAND-0021 (Category 4: Path Traversal / File Access)
Target Scope: Static files asset lookup
Intended Behavior: Checks canonical common path between base directory and target file,
preventing directory traversal (CWE-22) in static file handlers.
"""

from __future__ import annotations

import os


def is_safe_asset_path(base_dir: str, relative_path: str) -> bool:
    """Validate that the canonical target path resides within base directory."""
    if "\x00" in relative_path or ".." in relative_path:
        return False

    abs_base = os.path.abspath(base_dir)
    target_path = os.path.abspath(os.path.join(abs_base, relative_path.lstrip("/\\")))

    # Check that common prefix is exactly abs_base
    try:
        common = os.path.commonpath([abs_base, target_path])
        return common == abs_base
    except ValueError:
        # Happens on Windows if paths are on different drives
        return False
