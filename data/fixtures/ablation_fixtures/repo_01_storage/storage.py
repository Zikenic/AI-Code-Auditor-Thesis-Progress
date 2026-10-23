"""File storage module handling user uploads."""

from __future__ import annotations

import os
from pathlib import Path
from validators import sanitize_filename


def save_user_upload(upload_dir: str | Path, raw_filename: str, payload_data: bytes) -> str:
    """Save user-uploaded file safely within the designated upload directory.

    Delegates filename sanitization to `validators.sanitize_filename` to guarantee
    that file path traversal attempts (e.g. '../') are completely neutralized.
    """
    clean_name = sanitize_filename(raw_filename)
    target_dir = Path(upload_dir).resolve()
    target_path = (target_dir / clean_name).resolve()

    # Enforce base directory containment
    if not str(target_path).startswith(str(target_dir)):
        raise PermissionError("Attempted path escape outside root upload directory")

    target_dir.mkdir(parents=True, exist_ok=True)
    with open(target_path, "wb") as f:
        f.write(payload_data)

    return str(target_path)
