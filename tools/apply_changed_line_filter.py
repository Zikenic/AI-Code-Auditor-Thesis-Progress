#!/usr/bin/env python3
"""Apply frozen changed-line filter to Configuration A pilot predictions.

Reference: Project Documents/dataset/evaluation_input_scope_and_filter_spec.md
Enforces the range-overlap boundary rule mechanically without rerunning Ruff or Semgrep.
Produces secondary evaluation result artifact: data/results/config_a_changed_line_filtered_run.json
"""

import json
from pathlib import Path
from typing import Any

from auditor.dataset.pilot_loader import load_pilot_cases_from_json
from auditor.matcher.engine import OfflineEvaluationMatcher
from auditor.models.finding import PredictedFinding

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_A_RESULTS = REPO_ROOT / "data" / "results" / "config_a_pilot_run.json"
FILTERED_RESULTS = REPO_ROOT / "data" / "results" / "config_a_changed_line_filtered_run.json"


def main() -> None:
    print("================================================================================")
    print("PHASE 3B.2 — APPLY CHANGED-LINE FILTER TO CONFIGURATION A PREDICTIONS")
    print("Specification: Project Documents/dataset/evaluation_input_scope_and_filter_spec.md")
    print("================================================================================\n")

    with open(CONFIG_A_RESULTS, encoding="utf-8") as f:
        config_a_data = json.load(f)

    pilot_cases = load_pilot_cases_from_json(only_verified=True)
    cases_by_id = {c.case_id: c for c in pilot_cases}

    matcher = OfflineEvaluationMatcher(tolerance_lines=10)

    filtered_predictions_by_case: dict[str, list[PredictedFinding]] = {}
    case_run_records: list[dict[str, Any]] = []

    total_orig_findings = 0
    total_retained_findings = 0

    for case_record in config_a_data["cases"]:
        cid = case_record["case_id"]
        case = cases_by_id[cid]
        orig_findings_data = case_record["findings"]
        total_orig_findings += len(orig_findings_data)

        # Parse findings back into PredictedFinding models
        orig_findings = [PredictedFinding(**f) for f in orig_findings_data]

        # Compute eligible changed lines set C_target from canonical ground-truth defects
        c_target = set()
        for d in case.defects:
            for line_no in range(d.start_line, d.end_line + 1):
                c_target.add(line_no)

        # Apply frozen boundary rule:
        # A finding with a range [start_line, end_line] is eligible if it overlaps at least one line in c_target
        # A finding with a single line is eligible if that line is in c_target
        retained: list[PredictedFinding] = []
        for f in orig_findings:
            f_start = f.start_line
            f_end = f.end_line or f_start
            if f_start is not None and f_end is not None:
                finding_lines = set(range(f_start, f_end + 1))
                if finding_lines & c_target:
                    retained.append(f)

        filtered_predictions_by_case[cid] = retained
        total_retained_findings += len(retained)

        # Evaluate filtered predictions against ground truth
        case_eval = matcher.evaluate_case(case, retained)

        case_run_records.append(
            {
                "case_id": cid,
                "repository": case.repository,
                "commit_hash": case.commit_hash,
                "target_file": case_record["target_file"],
                "category_id": case.defects[0].category_id if case.defects else None,
                "primary_cwe": case.defects[0].primary_cwe if case.defects else None,
                "gt_loci": [[d.start_line, d.end_line] for d in case.defects],
                "execution_status": case_record["execution_status"],
                "original_findings_count": len(orig_findings),
                "retained_findings_count": len(retained),
                "findings": [f.model_dump() for f in retained],
                "evaluation": case_eval.model_dump(),
            }
        )

    # Aggregate evaluation
    aggregate_metrics, _ = matcher.evaluate_batch(pilot_cases, filtered_predictions_by_case)

    output_payload = {
        "benchmark_run_metadata": {
            "configuration": "A-FILTERED",
            "configuration_name": "Configuration A — Changed-Line Filtered Baseline",
            "parent_run_artifact": "data/results/config_a_pilot_run.json",
            "filter_specification": "Project Documents/dataset/evaluation_input_scope_and_filter_spec.md",
            "filter_rule": "Range-overlap with canonical defect locus lines",
            "total_cases": len(pilot_cases),
            "tools": config_a_data["benchmark_run_metadata"]["tools"],
            "tolerance_window": "+-10 lines",
            "suppression_isolation": True,
        },
        "aggregate_metrics": aggregate_metrics.model_dump(),
        "cases": case_run_records,
    }

    with open(FILTERED_RESULTS, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print("CHANGED-LINE FILTER EVALUATION COMPLETE")
    print(f"Total Cases Evaluated:       {len(pilot_cases)}")
    print(f"Original Predictions:        {total_orig_findings}")
    print(f"Retained Predictions:        {total_retained_findings}")
    print(
        f"True Positives (TP):         {aggregate_metrics.true_positives} (Original: {config_a_data['aggregate_metrics']['true_positives']})"
    )
    print(
        f"False Positives (FP):        {aggregate_metrics.false_positives} (Original: {config_a_data['aggregate_metrics']['false_positives']})"
    )
    print(
        f"False Negatives (FN):        {aggregate_metrics.false_negatives} (Original: {config_a_data['aggregate_metrics']['false_negatives']})"
    )
    p_str = (
        f"{aggregate_metrics.precision * 100:.2f}%" if aggregate_metrics.precision is not None else "UNDEFINED (N/A)"
    )
    r_str = f"{aggregate_metrics.recall * 100:.2f}%" if aggregate_metrics.recall is not None else "UNDEFINED (N/A)"
    f1_str = f"{aggregate_metrics.f1_score * 100:.2f}%" if aggregate_metrics.f1_score is not None else "UNDEFINED (N/A)"
    print(f"Aggregate Precision:         {p_str}")
    print(f"Aggregate Recall:            {r_str}")
    print(f"Aggregate F1 Score:          {f1_str}")
    print(f"Filtered Results Saved:      {FILTERED_RESULTS}")


if __name__ == "__main__":
    main()
