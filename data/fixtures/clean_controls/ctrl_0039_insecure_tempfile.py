"""Clean Control Fixture: CTRL-0039
Paired with: CAND-0039 (Category 4: Path Traversal / Unsafe File Operations)
Target Scope: Temporary file creation for intermediate processing
Intended Behavior: Uses NamedTemporaryFile ensuring atomic creation and private permissions.
"""

from __future__ import annotations
import tempfile

def write_cached_summary(content: str) -> str:
    """Write cached summary safely with atomic temp file."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as tf:
        tf.write(content)
        return tf.name
