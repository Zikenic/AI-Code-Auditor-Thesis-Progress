"""Clean Control Fixture: CTRL-0036
Paired with: CAND-0036 (Category 4: Path Traversal / Unsafe File Operations)
Target Scope: Compressed archive extraction directory safety
Intended Behavior: Validates each member target canonical path against destination.
"""

from __future__ import annotations
from pathlib import Path
import zipfile

def extract_archive(zip_path: str, destination_dir: str) -> None:
    """Extract zip archive members safely checking path boundaries."""
    dest = Path(destination_dir).resolve()
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            target_path = (dest / member.filename).resolve()
            if not target_path.is_relative_to(dest):
                raise ValueError(f"Illegal zip member path: {member.filename}")
            zf.extract(member, dest)
