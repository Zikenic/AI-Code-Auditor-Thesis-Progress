#!/usr/bin/env python3
"""Build derived 18-case Configuration A artifact by merging original 17-case baseline and CAND-0006 supplement.

Governance Invariants:
- Preserves data/results/config_a_pilot_run.json byte-for-byte unmodified.
- Integrates data/results/config_a_cand_0006_supplement.json.
- Re-evaluates aggregate metrics across all 18 cases / 23 ground truth defects using OfflineEvaluationMatcher.
- Outputs data/results/config_a_18_case_derived_run.json.
"""

from __future__ import annotations

import json
from pathlib import Path

from auditor.dataset.pilot_loader import load_pilot_cases_from_json
from auditor.matcher.engine import OfflineEvaluationMatcher
from auditor.models.finding import PredictedFinding

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "data" / "results"
CONFIG_A_ORIGINAL_FILE = RESULTS_DIR / "config_a_pilot_run.json"
CONFIG_A_SUPPLEMENT_FILE = RESULTS_DIR / "config_a_cand_0006_supplement.json"
CONFIG_A_DERIVED_FILE = RESULTS_DIR / "config_a_18_case_derived_run.json"


def main() -> None:
    print("================================================================================")
    print("CONSTRUCTING DERIVED 18-CASE CONFIGURATION A ARTIFACT")
    print("================================================================================\n")

    if not CONFIG_A_ORIGINAL_FILE.exists():
        raise FileNotFoundError(f"Original baseline not found: {CONFIG_A_ORIGINAL_FILE}")
    if not CONFIG_A_SUPPLEMENT_FILE.exists():
        raise FileNotFoundError(f"CAND-0006 supplement not found: {CONFIG_A_SUPPLEMENT_FILE}")

    with open(CONFIG_A_ORIGINAL_FILE, encoding="utf-8") as f:
        orig_data = json.load(f)
    with open(CONFIG_A_SUPPLEMENT_FILE, encoding="utf-8") as f:
        supp_data = json.load(f)

    # Load canonical benchmark cases (18 ground truth verified)
    canonical_cases = load_pilot_cases_from_json(only_verified=True)
    print(f"Loaded {len(canonical_cases)} canonical verified cases from data/pilot_cases.json.")

    # Combine case records
    combined_cases_records = list(orig_data["cases"])
    supp_cases_records = supp_data["cases"]

    # Verify no duplicate case IDs
    existing_case_ids = {c["case_id"] for c in combined_cases_records}
    for sc in supp_cases_records:
        if sc["case_id"] in existing_case_ids:
            print(f"Warning: {sc['case_id']} already exists in baseline. Replacing with supplement.")
            combined_cases_records = [c for c in combined_cases_records if c["case_id"] != sc["case_id"]]
        combined_cases_records.append(sc)

    # Sort in canonical pilot_cases order
    case_order = {c.case_id: idx for idx, c in enumerate(canonical_cases)}
    combined_cases_records.sort(key=lambda c: case_order.get(c["case_id"], 999))

    # Reconstruct predictions_by_case for OfflineEvaluationMatcher
    matcher = OfflineEvaluationMatcher(tolerance_lines=10)
    predictions_by_case: dict[str, list[PredictedFinding]] = {}

    for cr in combined_cases_records:
        cid = cr["case_id"]
        findings = [PredictedFinding.model_validate(f) for f in cr["findings"]]
        predictions_by_case[cid] = findings

    aggregate_metrics, per_case_results = matcher.evaluate_batch(canonical_cases, predictions_by_case)

    # Build derived run metadata
    total_duration = sum(c["duration_seconds"] for c in combined_cases_records)
    derived_metadata = {
        "configuration": "A",
        "configuration_name": "Configuration A — Deterministic Static Analysis Baseline (18-Case Composite)",
        "composition_provenance": {
            "is_derived_composite": True,
            "original_17_case_baseline_file": "data/results/config_a_pilot_run.json",
            "cand_0006_supplement_file": "data/results/config_a_cand_0006_supplement.json",
            "historical_baseline_preserved": True,
            "replaced_case": "CAND-0003",
            "replacement_case": "CAND-0006",
        },
        "timestamp_iso": supp_data["benchmark_run_metadata"]["timestamp_iso"],
        "total_cases": len(combined_cases_records),
        "total_duration_seconds": round(total_duration, 3),
        "tools": orig_data["benchmark_run_metadata"]["tools"],
        "tolerance_window": "+-10 lines",
        "suppression_isolation": True,
    }

    derived_payload = {
        "benchmark_run_metadata": derived_metadata,
        "aggregate_metrics": aggregate_metrics.model_dump(),
        "cases": combined_cases_records,
    }

    with open(CONFIG_A_DERIVED_FILE, "w", encoding="utf-8") as f:
        json.dump(derived_payload, f, indent=2)

    print("Successfully created derived 18-case artifact:")
    print(f"Path:                        {CONFIG_A_DERIVED_FILE}")
    print(f"Total Cases:                 {len(combined_cases_records)}")
    print(f"Total Ground-Truth Defects:  {aggregate_metrics.total_ground_truth_defects}")
    print(f"Total Predictions Emitted:   {aggregate_metrics.total_predictions}")
    print(f"True Positives (TP):         {aggregate_metrics.true_positives}")
    print(f"False Positives (FP):        {aggregate_metrics.false_positives}")
    print(f"False Negatives (FN):        {aggregate_metrics.false_negatives}")
    p_str = (
        f"{aggregate_metrics.precision * 100:.2f}%" if aggregate_metrics.precision is not None else "UNDEFINED (N/A)"
    )
    r_str = f"{aggregate_metrics.recall * 100:.2f}%" if aggregate_metrics.recall is not None else "UNDEFINED (N/A)"
    f1_str = f"{aggregate_metrics.f1_score * 100:.2f}%" if aggregate_metrics.f1_score is not None else "UNDEFINED (N/A)"
    print(f"Aggregate Precision:         {p_str}")
    print(f"Aggregate Recall:            {r_str}")
    print(f"Aggregate F1 Score:          {f1_str}")
    print("================================================================================\n")


if __name__ == "__main__":
    main()
