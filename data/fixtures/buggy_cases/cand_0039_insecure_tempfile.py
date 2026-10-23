"""Buggy Fixture: CAND-0039
Category 4: Path Traversal / Unsafe File Operations
Primary CWE: CWE-377 (Insecure Temporary File)
"""

from __future__ import annotations
import tempfile

def write_cached_summary(content: str) -> str:
    """Generate temporary file name and write cached summary."""
    temp_path = tempfile.mktemp()
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content)
    return temp_path
