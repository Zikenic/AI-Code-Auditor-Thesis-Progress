"""Offline evaluation benchmark matcher and scoring engine."""

from pydantic import BaseModel, Field

from auditor.matcher.bipartite import find_maximum_bipartite_matching
from auditor.matcher.location import check_location_match
from auditor.matcher.path_utils import normalize_repo_path
from auditor.models.finding import PredictedFinding
from auditor.models.ground_truth import BenchmarkCase, GroundTruthDefect
from auditor.models.result import EvaluationMetrics


class MatchPair(BaseModel):
    """Pair of a matched predicted finding and ground-truth defect."""

    finding_id: str
    defect_id: str
    file_path: str
    is_direct_overlap: bool
    matched_cwe: str


class CaseEvaluationResult(BaseModel):
    """Detailed evaluation result for a single benchmark case."""

    case_id: str
    is_buggy: bool
    true_positives: int = Field(default=0, ge=0)
    false_positives: int = Field(default=0, ge=0)
    false_negatives: int = Field(default=0, ge=0)
    matched_pairs: list[MatchPair] = Field(default_factory=list)
    unmatched_prediction_ids: list[str] = Field(default_factory=list)
    unmatched_defect_ids: list[str] = Field(default_factory=list)


class OfflineEvaluationMatcher:
    """Offline benchmark matcher implementing the locked methodology matching rules:

    1. File Match: Exact normalized repository-relative path comparison.
    2. CWE Match: Reported CWE matches primary CWE OR falls within pre-declared alternative_cwe_set.
    3. Location Match: Reported line range overlaps GT locus OR intersects uniform +-10 lines window.
    4. One-to-One Consumption: Maximum-cardinality bipartite matching consumes each defect at most once.
    5. Scoring:
       - Matched predictions = True Positives (TP)
       - Extra unmatched predictions on buggy PRs = False Positives (FP)
       - All predictions on clean PRs = False Positives (FP)
       - Unmatched ground-truth defects = False Negatives (FN)
    """

    def __init__(self, tolerance_lines: int = 10, repo_root_prefix: str | None = None):
        self.tolerance_lines = tolerance_lines
        self.repo_root_prefix = repo_root_prefix

    def is_candidate_match(
        self,
        pred: PredictedFinding,
        defect: GroundTruthDefect,
    ) -> tuple[bool, bool]:
        """Check if a predicted finding satisfies all 3 matching criteria against a GT defect.

        Returns:
            (is_match, is_direct_overlap)
        """
        # 1. Normalized File Path Match
        norm_pred_file = normalize_repo_path(pred.file_path, self.repo_root_prefix)
        norm_gt_file = normalize_repo_path(defect.file_path, self.repo_root_prefix)
        if norm_pred_file != norm_gt_file:
            return False, False

        # 2. Category / CWE Match
        if not defect.matches_cwe(pred.primary_cwe):
            return False, False

        # 3. Location Match (+-10 lines tolerance)
        is_loc_match, is_direct = check_location_match(
            gt_start=defect.start_line,
            gt_end=defect.end_line,
            pred_start=pred.start_line,
            pred_end=pred.end_line,
            tolerance=self.tolerance_lines,
        )

        return is_loc_match, is_direct

    def evaluate_case(
        self,
        case: BenchmarkCase,
        predictions: list[PredictedFinding],
    ) -> CaseEvaluationResult:
        """Evaluate predictions for a single benchmark case."""
        # Clean PR rule: zero GT defects; every emitted prediction is a False Positive
        if not case.is_buggy:
            return CaseEvaluationResult(
                case_id=case.case_id,
                is_buggy=False,
                true_positives=0,
                false_positives=len(predictions),
                false_negatives=0,
                matched_pairs=[],
                unmatched_prediction_ids=[p.finding_id for p in predictions],
                unmatched_defect_ids=[],
            )

        # Canonical sort for order-independent determinism
        sorted_preds = sorted(
            predictions,
            key=lambda p: (
                normalize_repo_path(p.file_path, self.repo_root_prefix),
                p.start_line or 0,
                p.end_line or 0,
                p.primary_cwe,
                p.finding_id,
            ),
        )
        sorted_defects = sorted(
            case.defects,
            key=lambda d: (
                normalize_repo_path(d.file_path, self.repo_root_prefix),
                d.start_line,
                d.end_line,
                d.primary_cwe,
                d.defect_id,
            ),
        )

        overlap_cache: dict[tuple[int, int], bool] = {}

        def can_match(p: PredictedFinding, d: GroundTruthDefect) -> bool:
            p_idx = sorted_preds.index(p)
            d_idx = sorted_defects.index(d)
            matched, direct = self.is_candidate_match(p, d)
            if matched:
                overlap_cache[(p_idx, d_idx)] = direct
            return matched

        def match_priority(p: PredictedFinding, d: GroundTruthDefect) -> tuple[int, int]:
            p_idx = sorted_preds.index(p)
            d_idx = sorted_defects.index(d)
            is_direct = 1 if overlap_cache.get((p_idx, d_idx), False) else 0
            # Prefer direct line overlap, then primary CWE match
            is_primary_cwe = 1 if p.primary_cwe == d.primary_cwe else 0
            return (is_direct, is_primary_cwe)

        matching = find_maximum_bipartite_matching(
            sorted_preds,
            sorted_defects,
            can_match=can_match,
            match_priority=match_priority,
        )

        matched_pred_indices = set(matching.keys())
        matched_defect_indices = set(matching.values())

        matched_pairs: list[MatchPair] = []
        for p_idx, d_idx in matching.items():
            pred = sorted_preds[p_idx]
            defect = sorted_defects[d_idx]
            matched_pairs.append(
                MatchPair(
                    finding_id=pred.finding_id,
                    defect_id=defect.defect_id,
                    file_path=normalize_repo_path(pred.file_path, self.repo_root_prefix),
                    is_direct_overlap=overlap_cache.get((p_idx, d_idx), False),
                    matched_cwe=pred.primary_cwe,
                )
            )

        unmatched_pred_ids = [p.finding_id for i, p in enumerate(sorted_preds) if i not in matched_pred_indices]
        unmatched_defect_ids = [d.defect_id for j, d in enumerate(sorted_defects) if j not in matched_defect_indices]

        tp = len(matched_pairs)
        fp = len(unmatched_pred_ids)
        fn = len(unmatched_defect_ids)

        return CaseEvaluationResult(
            case_id=case.case_id,
            is_buggy=True,
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            matched_pairs=matched_pairs,
            unmatched_prediction_ids=unmatched_pred_ids,
            unmatched_defect_ids=unmatched_defect_ids,
        )

    def evaluate_batch(
        self,
        cases: list[BenchmarkCase],
        predictions_by_case: dict[str, list[PredictedFinding]],
    ) -> tuple[EvaluationMetrics, list[CaseEvaluationResult]]:
        """Evaluate a full batch of benchmark cases against predictions.

        Returns:
            Tuple of (overall EvaluationMetrics, list of per-case CaseEvaluationResult).
        """
        case_results: list[CaseEvaluationResult] = []
        total_tp = 0
        total_fp = 0
        total_fn = 0
        clean_count = 0
        clean_flagged = 0
        buggy_count = 0
        total_preds = 0
        total_gt = 0

        for case in cases:
            preds = predictions_by_case.get(case.case_id, [])
            total_preds += len(preds)

            if case.is_buggy:
                buggy_count += 1
                total_gt += len(case.defects)
            else:
                clean_count += 1
                if len(preds) > 0:
                    clean_flagged += 1

            result = self.evaluate_case(case, preds)
            case_results.append(result)

            total_tp += result.true_positives
            total_fp += result.false_positives
            total_fn += result.false_negatives

        metrics = EvaluationMetrics.calculate(
            tp=total_tp,
            fp=total_fp,
            fn=total_fn,
            clean_cases=clean_count,
            clean_cases_flagged=clean_flagged,
            buggy_cases=buggy_count,
            total_predictions=total_preds,
            total_gt_defects=total_gt,
        )

        return metrics, case_results
