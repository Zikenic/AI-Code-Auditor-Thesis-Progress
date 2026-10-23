"""Clean Control Fixture: CTRL-0012
Paired with: CAND-0020 (Category 4: Path Traversal / File Access)
Target Scope: Uploaded filename sanitization and secure destination join
Intended Behavior: Strips directory components and path traversal markers from
filenames before saving uploads, preventing Path Traversal (CWE-22).
"""

from __future__ import annotations

import re
from pathlib import Path


def secure_filename(filename: str) -> str:
    """Sanitize filename by stripping directory separators and dangerous characters."""
    # Convert backslashes and forward slashes to space, then take basename
    clean = filename.replace("\\", "/").split("/")[-1].strip()
    # Keep only ASCII alphanumerics, dots, hyphens, and underscores
    clean = re.sub(r"[^A-Za-z0-9_.-]", "_", clean)
    clean = clean.lstrip(".")
    return clean or "unnamed_file"


def get_upload_path(upload_dir: Path, user_filename: str) -> Path:
    """Return secure destination path inside upload directory."""
    safe_name = secure_filename(user_filename)
    dest = (upload_dir / safe_name).resolve()
    if not dest.is_relative_to(upload_dir.resolve()):
        raise ValueError("Path traversal attempt detected")
    return dest
