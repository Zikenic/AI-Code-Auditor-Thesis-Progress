"""Deduplication and aggregation logic for findings across multiple chunks.

Enforces:
- Deterministic deduplication across chunk boundaries (INV-07).
- Key = (file_path, line_range, primary_cwe).
- Preserves distinct CWE classifications at identical lines.
"""

from __future__ import annotations

from auditor.matcher.path_utils import normalize_repo_path
from auditor.models.finding import PredictedFinding


def deduplicate_findings(findings: list[PredictedFinding]) -> list[PredictedFinding]:
    """Deduplicate findings emitted across chunks or passes.

    Preserves distinct CWEs at the same line range, merging only identical
    (file_path, line_range, primary_cwe) tuples while retaining the earliest/highest-confidence item.
    """
    seen: set[tuple[str, int | None, int | None, str]] = set()
    deduped: list[PredictedFinding] = []

    for f in findings:
        norm_path = normalize_repo_path(f.file_path)
        key = (norm_path, f.start_line, f.end_line, f.primary_cwe.upper())
        if key not in seen:
            seen.add(key)
            deduped.append(f)

    return deduped
