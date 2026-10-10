"""Auditor offline evaluation benchmark matcher package."""

from auditor.matcher.bipartite import find_maximum_bipartite_matching
from auditor.matcher.engine import (
    CaseEvaluationResult,
    MatchPair,
    OfflineEvaluationMatcher,
)
from auditor.matcher.location import (
    TOLERANCE_WINDOW_LINES,
    check_location_match,
    has_direct_overlap,
    matches_tolerance_window,
)
from auditor.matcher.path_utils import normalize_repo_path

__all__ = [
    "TOLERANCE_WINDOW_LINES",
    "CaseEvaluationResult",
    "MatchPair",
    "OfflineEvaluationMatcher",
    "check_location_match",
    "find_maximum_bipartite_matching",
    "has_direct_overlap",
    "matches_tolerance_window",
    "normalize_repo_path",
]
