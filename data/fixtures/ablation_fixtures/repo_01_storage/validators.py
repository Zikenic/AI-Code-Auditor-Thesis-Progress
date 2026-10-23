"""Filename validation and path sanitization helper."""

from __future__ import annotations

import os
import re
from pathlib import Path


def sanitize_filename(filename: str) -> str:
    """Sanitize user-supplied filename to prevent directory traversal attacks.

    Strips null bytes, path separators, parent directory markers ('..'),
    and restricts output strictly to safe alphanumeric and permitted punctuation.
    """
    if not filename:
        raise ValueError("Filename cannot be empty")

    # Reject null bytes
    if "\x00" in filename:
        raise ValueError("Filename contains forbidden null byte")

    # Extract base name to eliminate leading directory paths
    base = os.path.basename(filename.replace("\\", "/"))

    # Remove dangerous traversal patterns
    cleaned = re.sub(r"\.\.+", "", base).strip(" .")

    # Retain strictly safe ASCII alphanumeric characters and safe separators
    safe_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", cleaned)
    if not safe_name:
        raise ValueError("Sanitized filename resulted in empty string")

    return safe_name
