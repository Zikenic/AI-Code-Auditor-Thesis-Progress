"""Path normalization utilities for benchmark defect matching."""

import posixpath
import re


def normalize_repo_path(path: str, repo_root_prefix: str | None = None) -> str:
    """Normalize a repository file path for strict case-sensitive matching.

    1. Normalizes Windows backslashes '\\' to POSIX forward slashes '/'.
    2. Strips leading and trailing whitespace.
    3. Removes leading slashes and './' prefixes.
    4. Safely strips known repository-root prefixes if provided.
    5. Resolves relative '.' and '..' components using posixpath.normpath.
    6. Does NOT fall back to basename / filename-only matching.

    Args:
        path: Raw file path from prediction or ground truth.
        repo_root_prefix: Optional known repository root prefix (e.g. 'repo-name/', '/workspace/').

    Returns:
        Canonical repository-relative POSIX path (e.g. 'src/auditor/models.py').
    """
    if not path or not path.strip():
        return ""

    # Replace Windows backslashes with forward slashes
    clean = path.strip().replace("\\", "/")

    # Strip repo root prefix if specified
    if repo_root_prefix:
        norm_prefix = repo_root_prefix.strip().replace("\\", "/").rstrip("/") + "/"
        if clean.startswith(norm_prefix):
            clean = clean[len(norm_prefix) :]

    # Clean leading slashes
    clean = re.sub(r"^/+", "", clean)

    # Use posixpath.normpath to resolve internal '.' and '..'
    normalized = posixpath.normpath(clean)

    # Handle cases where normpath returns '.' for root
    if normalized == ".":
        return ""

    # Strip any remaining leading './'
    if normalized.startswith("./"):
        normalized = normalized[2:]

    return normalized
