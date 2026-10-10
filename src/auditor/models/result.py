"""Audit run results and evaluation metrics models."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from auditor.models.config import AuditConfiguration
from auditor.models.finding import PredictedFinding


class AuditStatus(StrEnum):
    """Lifecycle execution status of an audit run."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class AuditRunResult(BaseModel):
    """Output result of an audit execution run."""

    run_id: str = Field(..., description="Unique UUID for this audit execution.")
    request_id: str = Field(..., description="Originating AuditRequest ID.")
    configuration: AuditConfiguration = Field(..., description="Executed configuration (A, B, C, or D).")
    status: AuditStatus = Field(default=AuditStatus.SUCCESS, description="Execution outcome status.")
    findings: list[PredictedFinding] = Field(default_factory=list, description="List of emitted findings.")
    error_message: str | None = Field(default=None, description="Error message if run failed or partial.")
    provenance: dict[str, Any] = Field(
        default_factory=dict,
        description="Execution metadata (duration, token counts, tool versions).",
    )


class EvaluationMetrics(BaseModel):
    """Quantitative performance metrics computed by the evaluation matcher.

    Authoritative Specification Reference:
    Project Documents/dataset/dataset_design_test_case_list.md, Section 14, Lines 410–416:
    - Precision = TP / (TP + FP)
    - Recall = TP / (TP + FN)
    - F1 = 2 * (Precision * Recall) / (Precision + Recall)
    - False Positive Rate (FPR) = Clean PRs Flagged / Total Clean PRs

    Mathematical Undefined Values:
    - Precision is None if total predictions (TP + FP) == 0.
    - Recall is None if total ground-truth defects (TP + FN) == 0.
    - F1 is None if Precision or Recall is None, or both are 0.0.
    - FPR is None if Total Clean PRs == 0.
    """

    true_positives: int = Field(default=0, ge=0, description="Count of matched ground-truth defects.")
    false_positives: int = Field(
        default=0,
        ge=0,
        description="Count of unmatched predictions on buggy PRs plus all predictions on clean PRs.",
    )
    false_negatives: int = Field(default=0, ge=0, description="Count of missed ground-truth defects.")
    precision: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="TP / (TP + FP); None if total predictions (TP + FP) == 0.",
    )
    recall: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="TP / (TP + FN); None if total GT defects (TP + FN) == 0.",
    )
    f1_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="2 * (P * R) / (P + R); None if Precision or Recall is None, or P + R == 0.",
    )
    false_positive_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Clean PRs Flagged / Total Clean PRs (Dataset Specification Section 14, line 416); "
            "None if Total Clean PRs == 0."
        ),
    )

    # Diagnostic metadata
    clean_cases_evaluated: int = Field(default=0, ge=0)
    clean_cases_flagged: int = Field(default=0, ge=0)
    buggy_cases_evaluated: int = Field(default=0, ge=0)
    total_predictions: int = Field(default=0, ge=0)
    total_ground_truth_defects: int = Field(default=0, ge=0)

    @classmethod
    def calculate(
        cls,
        tp: int,
        fp: int,
        fn: int,
        clean_cases: int = 0,
        clean_cases_flagged: int = 0,
        buggy_cases: int = 0,
        total_predictions: int = 0,
        total_gt_defects: int = 0,
    ) -> "EvaluationMetrics":
        """Compute precision, recall, F1, and FPR safely handling zero denominators."""
        # Precision: undefined (None) if no predictions were emitted
        precision = float(tp) / float(tp + fp) if (tp + fp) > 0 else None

        # Recall: undefined (None) if no ground-truth defects exist in evaluated cases
        recall = float(tp) / float(tp + fn) if (tp + fn) > 0 else None

        # F1: undefined (None) if precision or recall is undefined or their sum is zero
        if precision is not None and recall is not None and (precision + recall) > 0.0:
            f1 = (2.0 * precision * recall) / (precision + recall)
            f1_val = round(f1, 4)
        else:
            f1_val = None

        # False Positive Rate (FPR): Section 14, line 416
        # FPR = Clean PRs Flagged / Total Clean PRs
        if clean_cases > 0:
            fpr_val = round(float(clean_cases_flagged) / float(clean_cases), 4)
        else:
            fpr_val = None

        return cls(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            precision=round(precision, 4) if precision is not None else None,
            recall=round(recall, 4) if recall is not None else None,
            f1_score=f1_val,
            false_positive_rate=fpr_val,
            clean_cases_evaluated=clean_cases,
            clean_cases_flagged=clean_cases_flagged,
            buggy_cases_evaluated=buggy_cases,
            total_predictions=total_predictions,
            total_ground_truth_defects=total_gt_defects,
        )
