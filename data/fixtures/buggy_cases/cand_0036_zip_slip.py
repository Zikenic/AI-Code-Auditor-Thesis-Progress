"""Buggy Fixture: CAND-0036
Category 4: Path Traversal / Unsafe File Operations
Primary CWE: CWE-22 (Zip Slip File Overwrite via Path Traversal)
"""

from __future__ import annotations
import zipfile

def extract_archive(zip_path: str, destination_dir: str) -> None:
    """Extract zip archive files into target directory."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(destination_dir)
