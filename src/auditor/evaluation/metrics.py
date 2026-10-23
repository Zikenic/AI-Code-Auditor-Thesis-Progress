"""Evaluation Metrics and Benchmark Scoring Module.

Calculates:
- True Positives (TP), False Positives (FP), False Negatives (FN)
- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2 * (P * R) / (P + R)
- Clean-Case False-Positive Rate (FPR) = Clean PRs Flagged / Total Clean PRs
- Defect Case Detection Rate = Buggy PRs with >=1 TP / Total Buggy PRs
- Config C hybrid triage metrics: preserved findings, confirmed, likely FP, additional candidates
- Config D incremental metrics: delta TP, delta FP, context latency/overhead
- Excluded unknown expectation cases
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from auditor.evaluation.manifest import AnnotationCompleteness, AnnotationState, ManifestCase
from auditor.evaluation.provenance import ResultProvenance, determine_case_eligibility
from auditor.matcher.engine import CaseEvaluationResult, OfflineEvaluationMatcher
from auditor.models.finding import DetectionLayer, PredictedFinding, TriageStatus


class ConfigurationMetrics(BaseModel):
    """Calculated benchmark performance metrics for a specific configuration."""

    configuration: str = Field(..., description="Configuration evaluated ('A', 'B', 'C', or 'D').")
    total_cases_evaluated: int = Field(default=0, ge=0)
    cases_attempted: int = Field(default=0, ge=0)
    cases_successful: int = Field(default=0, ge=0)
    cases_failed: int = Field(default=0, ge=0)
    cases_partial: int = Field(default=0, ge=0)
    cases_skipped: int = Field(default=0, ge=0)

    buggy_cases_evaluated: int = Field(default=0, ge=0)
    clean_cases_evaluated: int = Field(default=0, ge=0)
    clean_cases_attempted: int = Field(default=0, ge=0)
    clean_cases_successful: int = Field(default=0, ge=0)
    clean_cases_mocked_count: int = Field(default=0, ge=0)
    unknown_cases_excluded: int = Field(default=0, ge=0)

    true_positives: int = Field(default=0, ge=0)
    false_positives: int = Field(default=0, ge=0)
    confirmed_false_positives: int = Field(default=0, ge=0)
    unadjudicated_predictions: int = Field(default=0, ge=0)
    false_negatives: int = Field(default=0, ge=0)
    total_predictions: int = Field(default=0, ge=0)
    total_ground_truth_defects: int = Field(default=0, ge=0)

    precision: float | None = Field(default=None)
    historical_naive_precision: float | None = Field(default=None)
    confirmed_precision: float | None = Field(default=None)
    confirmed_precision_status: str = Field(default="eligible")
    confirmed_precision_note: str | None = Field(default=None)
    recall: float | None = Field(default=None)
    f1_score: float | None = Field(default=None)

    clean_cases_flagged: int = Field(default=0, ge=0)
    clean_case_false_positive_rate: float | None = Field(default=None)
    clean_case_fpr_status: str = Field(default="eligible")
    clean_case_fpr_note: str | None = Field(default=None)

    buggy_cases_detected: int = Field(default=0, ge=0)
    defect_case_detection_rate: float | None = Field(default=None)

    failed_runs_count: int = Field(default=0, ge=0)
    partial_runs_count: int = Field(default=0, ge=0)

    # Config C & Hybrid Specific Metrics
    static_findings_total: int = Field(default=0, ge=0)
    static_findings_preserved: int = Field(default=0, ge=0)
    static_findings_confirmed: int = Field(default=0, ge=0)
    static_findings_likely_fp: int = Field(default=0, ge=0)
    static_findings_inconclusive: int = Field(default=0, ge=0)
    additional_llm_candidates: int = Field(default=0, ge=0)
    triage_correct_fp_count: int = Field(default=0, ge=0)
    triage_incorrect_fp_count: int = Field(default=0, ge=0)

    # Config D Specific Comparison Metrics
    incremental_tp_over_c: int | None = Field(default=None)
    incremental_fp_over_c: int | None = Field(default=None)

    # Common successfully evaluated subset metrics
    common_subset_metrics: dict[str, Any] | None = Field(default=None)

    # Provenance summary
    provenance_breakdown: dict[str, int] = Field(default_factory=dict)
    is_mock_evaluation: bool = Field(default=False)

    # Telemetry
    total_duration_seconds: float = Field(default=0.0)
    total_cost_usd: float | None = Field(default=None)


class CaseEvaluationDetail(BaseModel):
    """Detailed per-case evaluation record."""

    case_id: str
    configuration: str
    is_buggy: bool
    annotation_state: AnnotationState
    annotation_completeness: str = "partial"
    provenance: str = "unknown"
    model_id: str | None = None
    execution_status: str
    duration_seconds: float
    true_positives: int
    false_positives: int
    confirmed_false_positives: int = 0
    unadjudicated_predictions: int = 0
    false_negatives: int
    emitted_findings_count: int
    matched_pairs: list[dict[str, Any]] = Field(default_factory=list)
    unmatched_prediction_ids: list[str] = Field(default_factory=list)
    unmatched_defect_ids: list[str] = Field(default_factory=list)
    metric_eligibility: dict[str, bool] = Field(default_factory=dict)
    exclusion_reasons: dict[str, str] = Field(default_factory=dict)
    failure_reason: str | None = None
    triage_summary: dict[str, int] = Field(default_factory=dict)


def compute_configuration_metrics(
    configuration: str,
    manifest_cases: list[ManifestCase],
    predictions_by_case: dict[str, list[PredictedFinding]],
    statuses_by_case: dict[str, str] | None = None,
    durations_by_case: dict[str, float] | None = None,
    provenance_by_case: dict[str, dict[str, Any]] | None = None,
    cost_usd: float | None = None,
    tolerance_lines: int = 10,
    config_c_baseline: ConfigurationMetrics | None = None,
    common_case_ids: set[str] | None = None,
) -> tuple[ConfigurationMetrics, list[CaseEvaluationDetail]]:
    """Compute formal evaluation metrics for a configuration run against manifest cases."""
    matcher = OfflineEvaluationMatcher(tolerance_lines=tolerance_lines)
    case_details: list[CaseEvaluationDetail] = []

    statuses = statuses_by_case or {}
    durations = durations_by_case or {}
    prov_map = provenance_by_case or {}

    total_tp = 0
    total_fp = 0
    total_confirmed_fp = 0
    total_unadjudicated = 0
    total_fn = 0
    total_preds = 0
    total_gt = 0

    cases_attempted = len(manifest_cases)
    cases_successful = 0
    cases_partial = 0
    cases_failed = 0
    cases_skipped = 0

    buggy_evaluated = 0
    buggy_detected = 0
    clean_attempted = 0
    clean_successful = 0
    clean_flagged = 0
    clean_mocked_count = 0
    unknown_excluded = 0

    provenance_breakdown: dict[str, int] = {}

    # Config C tallies
    static_total = 0
    static_preserved = 0
    static_confirmed = 0
    static_likely_fp = 0
    static_inconclusive = 0
    additional_candidates = 0
    triage_correct_fp = 0
    triage_incorrect_fp = 0

    for mcase in manifest_cases:
        cid = mcase.case_id
        preds = predictions_by_case.get(cid, [])
        status = statuses.get(cid, "success").lower()
        dur = durations.get(cid, 0.0)

        prov_entry = prov_map.get(cid, {})
        prov_src_raw = str(prov_entry.get("source", "unknown_provenance")).lower()
        prov_model = prov_entry.get("model")

        if "mock" in prov_src_raw:
            prov_enum = ResultProvenance.MOCK
        elif "deterministic" in prov_src_raw or "static" in prov_src_raw:
            prov_enum = ResultProvenance.REAL_DETERMINISTIC
        elif "frozen" in prov_src_raw or "historical" in prov_src_raw:
            prov_enum = ResultProvenance.FROZEN_HISTORICAL
        elif "live" in prov_src_raw or "real_model" in prov_src_raw:
            prov_enum = ResultProvenance.REAL_MODEL
        else:
            try:
                prov_enum = ResultProvenance(prov_src_raw)
            except ValueError:
                prov_enum = ResultProvenance.UNKNOWN

        prov_src = prov_enum.value
        provenance_breakdown[prov_src] = provenance_breakdown.get(prov_src, 0) + 1
        is_mock = prov_enum == ResultProvenance.MOCK

        if status in ("success", "completed"):
            cases_successful += 1
        elif status == "partial":
            cases_partial += 1
        elif status == "failed":
            cases_failed += 1
        elif status == "skipped":
            cases_skipped += 1

        is_clean = not mcase.is_buggy or mcase.annotation_state == AnnotationState.CLEAN
        is_exhaustive = mcase.annotation_completeness == AnnotationCompleteness.EXHAUSTIVE

        if is_clean:
            clean_attempted += 1
            if is_mock:
                clean_mocked_count += 1
            if status in ("success", "completed", "partial"):
                clean_successful += 1

        # Track Config C triage statistics across all predictions
        case_triage_counts = {"confirmed": 0, "likely_false_positive": 0, "inconclusive": 0, "additional": 0}
        for p in preds:
            layer = str(p.detection_layer)
            triage_val = (p.provenance or {}).get("triage")

            if layer == str(DetectionLayer.DETERMINISTIC_STATIC):
                static_total += 1
                static_preserved += 1
                if triage_val == TriageStatus.CONFIRMED.value:
                    static_confirmed += 1
                    case_triage_counts["confirmed"] += 1
                elif triage_val == TriageStatus.LIKELY_FALSE_POSITIVE.value:
                    static_likely_fp += 1
                    case_triage_counts["likely_false_positive"] += 1
                elif triage_val == TriageStatus.INCONCLUSIVE.value:
                    static_inconclusive += 1
                    case_triage_counts["inconclusive"] += 1
            elif layer == str(DetectionLayer.HEURISTIC_LLM):
                additional_candidates += 1
                case_triage_counts["additional"] += 1

        elig, excl = determine_case_eligibility(
            provenance=prov_enum,
            is_buggy=mcase.is_buggy,
            status=status,
        )

        # If annotation state is UNKNOWN, exclude from verified GT metrics
        if mcase.annotation_state == AnnotationState.UNKNOWN:
            unknown_excluded += 1
            case_details.append(
                CaseEvaluationDetail(
                    case_id=cid,
                    configuration=configuration,
                    is_buggy=mcase.is_buggy,
                    annotation_state=mcase.annotation_state,
                    annotation_completeness=mcase.annotation_completeness.value,
                    provenance=prov_src,
                    model_id=prov_model,
                    execution_status=status,
                    duration_seconds=round(dur, 3),
                    true_positives=0,
                    false_positives=len(preds),
                    confirmed_false_positives=0,
                    unadjudicated_predictions=len(preds),
                    false_negatives=0,
                    emitted_findings_count=len(preds),
                    metric_eligibility=elig,
                    exclusion_reasons=excl,
                    triage_summary=case_triage_counts,
                )
            )
            continue

        bcase = mcase.to_benchmark_case()
        eval_res: CaseEvaluationResult = matcher.evaluate_case(bcase, preds)

        total_preds += len(preds)
        total_tp += eval_res.true_positives
        total_fp += eval_res.false_positives
        total_fn += eval_res.false_negatives

        # Distinguish confirmed false positives from unadjudicated findings
        if is_clean:
            if not is_mock and status in ("success", "completed", "partial"):
                case_confirmed_fp = len(preds)
                if len(preds) > 0:
                    clean_flagged += 1
            else:
                case_confirmed_fp = 0
            case_unadjudicated = 0
        else:
            buggy_evaluated += 1
            total_gt += len(bcase.defects)
            if eval_res.true_positives > 0:
                buggy_detected += 1

            if is_exhaustive:
                case_confirmed_fp = eval_res.false_positives
                case_unadjudicated = 0
            else:
                case_confirmed_fp = 0
                case_unadjudicated = eval_res.false_positives

        total_confirmed_fp += case_confirmed_fp
        total_unadjudicated += case_unadjudicated

        # Evaluate triage accuracy against GT matches
        matched_pred_ids = {p.finding_id for p in eval_res.matched_pairs}
        for p in preds:
            triage_val = (p.provenance or {}).get("triage")
            if triage_val == TriageStatus.LIKELY_FALSE_POSITIVE.value:
                # If marked false positive and was NOT a GT match, it was a correct triage of a static FP
                if p.finding_id not in matched_pred_ids:
                    triage_correct_fp += 1
                else:
                    triage_incorrect_fp += 1

        case_details.append(
            CaseEvaluationDetail(
                case_id=cid,
                configuration=configuration,
                is_buggy=bcase.is_buggy,
                annotation_state=mcase.annotation_state,
                annotation_completeness=mcase.annotation_completeness.value,
                provenance=prov_src,
                model_id=prov_model,
                execution_status=status,
                duration_seconds=round(dur, 3),
                true_positives=eval_res.true_positives,
                false_positives=eval_res.false_positives,
                confirmed_false_positives=case_confirmed_fp,
                unadjudicated_predictions=case_unadjudicated,
                false_negatives=eval_res.false_negatives,
                emitted_findings_count=len(preds),
                matched_pairs=[p.model_dump() for p in eval_res.matched_pairs],
                unmatched_prediction_ids=eval_res.unmatched_prediction_ids,
                unmatched_defect_ids=eval_res.unmatched_defect_ids,
                metric_eligibility=elig,
                exclusion_reasons=excl,
                triage_summary=case_triage_counts,
            )
        )

    # Standard metrics
    precision = (total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else None
    recall = (total_tp / (total_tp + total_fn)) if (total_tp + total_fn) > 0 else None
    f1 = (
        (2 * precision * recall / (precision + recall))
        if (precision is not None and recall is not None and (precision + recall) > 0)
        else None
    )

    # Confirmed precision
    if total_unadjudicated > 0:
        confirmed_prec = None
        confirmed_prec_status = "unavailable_unadjudicated"
        confirmed_prec_note = f"Unavailable: {total_unadjudicated} predictions are unadjudicated outside annotated loci."
    elif (total_tp + total_confirmed_fp) > 0:
        confirmed_prec = total_tp / (total_tp + total_confirmed_fp)
        confirmed_prec_status = "eligible"
        confirmed_prec_note = None
    else:
        confirmed_prec = None
        confirmed_prec_status = "unavailable_zero_denominator"
        confirmed_prec_note = "Unavailable: Zero predictions emitted."

    # Clean-case FPR calculation
    if clean_mocked_count > 0:
        clean_fpr = None
        clean_fpr_status = "unavailable_mock"
        clean_fpr_note = f"Unavailable: {clean_mocked_count} clean controls evaluated with mock LLM outputs. Mock results cannot establish empirical model false-positive rate."
    elif clean_successful > 0:
        clean_fpr = clean_flagged / clean_successful
        clean_fpr_status = "eligible"
        clean_fpr_note = f"Observed warning rate on curated sample ({clean_flagged}/{clean_successful} clean fixtures flagged)."
    else:
        clean_fpr = None
        clean_fpr_status = "unavailable_zero_denominator"
        clean_fpr_note = "Unavailable: Zero clean cases successfully evaluated."

    det_rate = (buggy_detected / buggy_evaluated) if buggy_evaluated > 0 else None

    # Config D comparison with Config C
    delta_tp = None
    delta_fp = None
    if configuration.upper() == "D" and config_c_baseline:
        delta_tp = total_tp - config_c_baseline.true_positives
        delta_fp = total_fp - config_c_baseline.false_positives

    # Common subset metrics
    common_metrics = None
    if common_case_ids is not None:
        c_tp = 0
        c_fp = 0
        c_fn = 0
        c_count = 0
        for cd in case_details:
            if cd.case_id in common_case_ids:
                c_count += 1
                c_tp += cd.true_positives
                c_fp += cd.false_positives
                c_fn += cd.false_negatives
        c_prec = (c_tp / (c_tp + c_fp)) if (c_tp + c_fp) > 0 else None
        c_rec = (c_tp / (c_tp + c_fn)) if (c_tp + c_fn) > 0 else None
        c_f1 = (2 * c_prec * c_rec / (c_prec + c_rec)) if (c_prec and c_rec and (c_prec + c_rec) > 0) else None
        common_metrics = {
            "cases_count": c_count,
            "true_positives": c_tp,
            "false_positives": c_fp,
            "false_negatives": c_fn,
            "precision": round(c_prec, 4) if c_prec is not None else None,
            "recall": round(c_rec, 4) if c_rec is not None else None,
            "f1_score": round(c_f1, 4) if c_f1 is not None else None,
        }

    metrics = ConfigurationMetrics(
        configuration=configuration.upper(),
        total_cases_evaluated=len(manifest_cases),
        cases_attempted=cases_attempted,
        cases_successful=cases_successful,
        cases_failed=cases_failed,
        cases_partial=cases_partial,
        cases_skipped=cases_skipped,
        buggy_cases_evaluated=buggy_evaluated,
        clean_cases_evaluated=clean_successful,
        clean_cases_attempted=clean_attempted,
        clean_cases_successful=clean_successful,
        clean_cases_mocked_count=clean_mocked_count,
        unknown_cases_excluded=unknown_excluded,
        true_positives=total_tp,
        false_positives=total_fp,
        confirmed_false_positives=total_confirmed_fp,
        unadjudicated_predictions=total_unadjudicated,
        false_negatives=total_fn,
        total_predictions=total_preds,
        total_ground_truth_defects=total_gt,
        precision=round(precision, 4) if precision is not None else None,
        historical_naive_precision=round(precision, 4) if precision is not None else None,
        confirmed_precision=round(confirmed_prec, 4) if confirmed_prec is not None else None,
        confirmed_precision_status=confirmed_prec_status,
        confirmed_precision_note=confirmed_prec_note,
        recall=round(recall, 4) if recall is not None else None,
        f1_score=round(f1, 4) if f1 is not None else None,
        clean_cases_flagged=clean_flagged,
        clean_case_false_positive_rate=round(clean_fpr, 4) if clean_fpr is not None else None,
        clean_case_fpr_status=clean_fpr_status,
        clean_case_fpr_note=clean_fpr_note,
        buggy_cases_detected=buggy_detected,
        defect_case_detection_rate=round(det_rate, 4) if det_rate is not None else None,
        failed_runs_count=cases_failed,
        partial_runs_count=cases_partial,
        static_findings_total=static_total,
        static_findings_preserved=static_preserved,
        static_findings_confirmed=static_confirmed,
        static_findings_likely_fp=static_likely_fp,
        static_findings_inconclusive=static_inconclusive,
        additional_llm_candidates=additional_candidates,
        triage_correct_fp_count=triage_correct_fp,
        triage_incorrect_fp_count=triage_incorrect_fp,
        incremental_tp_over_c=delta_tp,
        incremental_fp_over_c=delta_fp,
        common_subset_metrics=common_metrics,
        provenance_breakdown=provenance_breakdown,
        is_mock_evaluation="mock" in [p.lower() for p in provenance_breakdown.keys()],
        total_duration_seconds=round(sum(durations.values()), 3),
        total_cost_usd=cost_usd,
    )

    return metrics, case_details
