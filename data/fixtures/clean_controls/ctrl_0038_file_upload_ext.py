"""Clean Control Fixture: CTRL-0038
Paired with: CAND-0038 (Category 4: Path Traversal / Unsafe File Operations)
Target Scope: User avatar file upload name and extension sanitization
Intended Behavior: Generates random UUID filename preserving only safe extension.
"""

from __future__ import annotations
from pathlib import Path
import uuid

UPLOAD_DIR = Path("/var/www/uploads").resolve()

def save_uploaded_avatar(client_filename: str, file_bytes: bytes) -> str:
    """Store avatar safely generating random server-managed filename."""
    ext = Path(client_filename).suffix.lower()
    if ext != ".png":
        raise ValueError("Only PNG supported.")
    safe_name = f"{uuid.uuid4().hex}{ext}"
    save_path = UPLOAD_DIR / safe_name
    with open(save_path, "wb") as f:
        f.write(file_bytes)
    return str(save_path)
