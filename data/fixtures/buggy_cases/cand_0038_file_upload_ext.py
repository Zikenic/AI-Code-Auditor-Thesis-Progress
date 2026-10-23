"""Buggy Fixture: CAND-0038
Category 4: Path Traversal / Unsafe File Operations
Primary CWE: CWE-434 (Unrestricted Upload of File with Dangerous Type)
"""

from __future__ import annotations
import os

UPLOAD_DIR = "/var/www/uploads"

def save_uploaded_avatar(client_filename: str, file_bytes: bytes) -> str:
    """Store avatar file on disk using client-provided filename."""
    if client_filename.endswith(".png"):
        save_path = os.path.join(UPLOAD_DIR, client_filename)
        with open(save_path, "wb") as f:
            f.write(file_bytes)
        return save_path
    raise ValueError("Only PNG supported.")
