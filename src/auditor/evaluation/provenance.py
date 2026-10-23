"""Result Provenance and Metric Eligibility Contracts for AI Code Auditor Benchmark.

Enforces strict scientific classification of evaluation outputs:
- real_deterministic: Actual static analysis (Ruff/Semgrep) executed on verified input.
- real_model: Actual completed LLM request with provider/model metadata.
- frozen_historical: Historical experiment output loaded from frozen prior artifact.
- mock: Deterministic fake or test double (validates logic, NEVER empirical accuracy).
- unknown_provenance: Execution origin not established.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ResultProvenance(StrEnum):
    """Scientific execution origin of a benchmark result."""

    REAL_DETERMINISTIC = "real_deterministic"
    REAL_MODEL = "real_model"
    FROZEN_HISTORICAL = "frozen_historical"
    MOCK = "mock"
    UNKNOWN = "unknown_provenance"


class CaseProvenanceRecord(BaseModel):
    """Detailed provenance tracking for a single evaluated case."""

    case_id: str = Field(..., description="Stable case identifier (e.g. 'CAND-0001', 'CTRL-0001').")
    configuration: str = Field(..., description="Evaluated configuration (A, B, C, D).")
    provenance: ResultProvenance = Field(..., description="Execution origin classification.")
    execution_status: str = Field(..., description="Status of the run: success, partial, failed, skipped.")
    dataset_source_revision: str = Field(..., description="Git commit hash, fixture path, or dataset version.")
    model_id: str | None = Field(default=None, description="LLM model identifier if applicable.")
    provider: str | None = Field(default=None, description="Provider/gateway name if applicable.")
    artifact_path: str | None = Field(default=None, description="Path to source result artifact if replayed.")
    failure_reason: str | None = Field(default=None, description="Documented error or exception text.")
    metric_eligibility: dict[str, bool] = Field(
        default_factory=dict,
        description="Map of metric names to boolean eligibility.",
    )
    exclusion_reasons: dict[str, str] = Field(
        default_factory=dict,
        description="Detailed justification for metric exclusion.",
    )

    def is_eligible_for_clean_fpr(self) -> bool:
        """Only real deterministic or real model runs are eligible for empirical clean FPR."""
        if self.provenance == ResultProvenance.MOCK:
            return False
        if self.provenance == ResultProvenance.UNKNOWN:
            return False
        return self.execution_status in ("success", "completed", "partial")

    def is_eligible_for_recall(self) -> bool:
        """Recall can be computed for real deterministic, real model, or frozen historical runs."""
        if self.provenance in (ResultProvenance.REAL_DETERMINISTIC, ResultProvenance.REAL_MODEL, ResultProvenance.FROZEN_HISTORICAL):
            return self.execution_status in ("success", "completed")
        return False


def determine_case_eligibility(
    provenance: ResultProvenance,
    is_buggy: bool,
    status: str,
) -> tuple[dict[str, bool], dict[str, str]]:
    """Determine metric eligibility and exclusion reasons for a case run."""
    eligibility: dict[str, bool] = {}
    exclusions: dict[str, str] = {}

    status_norm = status.lower()
    is_success = status_norm in ("success", "completed")

    # Recall eligibility
    if not is_buggy:
        eligibility["recall"] = False
        exclusions["recall"] = "Clean control case contains no gold defects."
    elif not is_success:
        eligibility["recall"] = False
        exclusions["recall"] = f"Run status '{status}' did not complete successfully."
    elif provenance == ResultProvenance.MOCK:
        eligibility["recall"] = False
        exclusions["recall"] = "Mock outputs cannot be used for empirical defect recall."
    elif provenance == ResultProvenance.UNKNOWN:
        eligibility["recall"] = False
        exclusions["recall"] = "Unknown provenance excluded from empirical metrics."
    else:
        eligibility["recall"] = True

    # Clean FPR eligibility
    if is_buggy:
        eligibility["clean_fpr"] = False
        exclusions["clean_fpr"] = "Defective case is not part of the clean control denominator."
    elif provenance == ResultProvenance.MOCK:
        eligibility["clean_fpr"] = False
        exclusions["clean_fpr"] = "Mock outputs cannot be used to establish empirical model false-positive rate."
    elif provenance == ResultProvenance.UNKNOWN:
        eligibility["clean_fpr"] = False
        exclusions["clean_fpr"] = "Unknown provenance excluded from empirical clean FPR."
    elif status_norm not in ("success", "completed", "partial"):
        eligibility["clean_fpr"] = False
        exclusions["clean_fpr"] = f"Run status '{status}' failed on clean control."
    else:
        eligibility["clean_fpr"] = True

    # Confirmed Precision eligibility
    if provenance == ResultProvenance.MOCK:
        eligibility["confirmed_precision"] = False
        exclusions["confirmed_precision"] = "Mock predictions cannot be used for empirical precision."
    else:
        eligibility["confirmed_precision"] = is_success

    return eligibility, exclusions
