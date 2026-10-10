#!/usr/bin/env python3
"""Execute Configuration B Benchmark Run across all 18 Canonical Pilot Cases.

Adheres strictly to:
- Phase 4B specifications and frozen parameters.
- Model: Claude Sonnet 4.6 (gateway ID: ag/claude-sonnet-4-6).
- Adaptive thinking with medium effort, temperature omitted.
- Max output allowance: 16,384 tokens per request.
- Measured-source chunking under B_source = 16,000 tokens.
- Budget allocation ceiling: $8.00 USD.
- Saves raw responses, telemetry, and parsed findings to data/results/config_b_pilot_run.json.
- Evaluates against ground-truth using OfflineEvaluationMatcher(tolerance_lines=10).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from auditor.dataset.pilot_loader import load_pilot_cases_from_json
from auditor.dataset.source_resolver import extract_target_file_content, resolve_case_repo_path
from auditor.llm.anthropic_client import AnthropicApiClient
from auditor.llm.config import DEFAULT_CONFIG_B_PARAMS
from auditor.llm.credentials import load_gateway_credentials
from auditor.llm.engine import ConfigBAuditEngine
from auditor.matcher.engine import OfflineEvaluationMatcher
from auditor.models.finding import PredictedFinding
from auditor.models.ground_truth import BenchmarkCase

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "data" / "results"
CONFIG_B_RESULTS_FILE = RESULTS_DIR / "config_b_pilot_run.json"


def run_benchmark(output_file: Path = CONFIG_B_RESULTS_FILE) -> dict[str, Any]:
    print("================================================================================")
    print("CONFIGURATION B BENCHMARK EXECUTION — 18 CANONICAL PILOT CASES")
    print(f"Model: {DEFAULT_CONFIG_B_PARAMS.display_name} ({DEFAULT_CONFIG_B_PARAMS.gateway_model_id})")
    print(f"Thinking: {DEFAULT_CONFIG_B_PARAMS.thinking_type} | Effort: {DEFAULT_CONFIG_B_PARAMS.thinking_effort}")
    print(f"Max completion tokens: {DEFAULT_CONFIG_B_PARAMS.max_completion_tokens}")
    print(f"Budget ceiling: ${DEFAULT_CONFIG_B_PARAMS.budget_ceiling_usd:.2f} USD")
    print("================================================================================\n")

    creds = load_gateway_credentials()
    api_client = AnthropicApiClient(credentials=creds, timeout=300.0, max_retries=3)
    engine = ConfigBAuditEngine(api_client=api_client, config=DEFAULT_CONFIG_B_PARAMS)
    matcher = OfflineEvaluationMatcher(tolerance_lines=10)

    cases: list[BenchmarkCase] = load_pilot_cases_from_json(only_verified=True)
    total_cases = len(cases)
    case_records: list[dict[str, Any]] = []
    predictions_by_case: dict[str, list[PredictedFinding]] = {}

    start_total_time = time.time()

    for idx, case in enumerate(cases, 1):
        target_file = case.defects[0].file_path if case.defects else ""
        repo_path = resolve_case_repo_path(case)
        raw_source = extract_target_file_content(repo_path, case.commit_hash, target_file)

        print(f"[{idx}/{total_cases}] Auditing {case.case_id} ({case.repository}) - {target_file}...", flush=True)

        case_start = time.time()
        status, findings, telemetry = engine.audit_source(
            raw_source=raw_source,
            file_path=target_file,
            case_id=case.case_id,
        )
        case_duration = time.time() - case_start
        predictions_by_case[case.case_id] = findings

        case_eval = matcher.evaluate_case(case, findings)

        spent_so_far = engine.cost_tracker.total_cost()
        chunks_count = telemetry.get("total_chunks", 1)
        tier_used = telemetry.get("tier_used", 1)

        print(
            f"       Status: {status.value} | Chunks: {chunks_count} (Tier {tier_used}) | "
            f"Findings: {len(findings)} | TP: {case_eval.true_positives} | FP: {case_eval.false_positives} | "
            f"FN: {case_eval.false_negatives} | Latency: {case_duration:.2f}s | Spent Pool: ${spent_so_far:.4f}",
            flush=True,
        )
        for pair in case_eval.matched_pairs:
            print(
                f"         * MATCHED: {pair.defect_id} with finding {pair.finding_id} ({pair.matched_cwe}, direct={pair.is_direct_overlap})",
                flush=True,
            )

        case_records.append(
            {
                "case_id": case.case_id,
                "repository": case.repository,
                "commit_hash": case.commit_hash,
                "target_file": target_file,
                "category_id": case.defects[0].category_id if case.defects else None,
                "primary_cwe": case.defects[0].primary_cwe if case.defects else None,
                "gt_loci": [[d.start_line, d.end_line] for d in case.defects],
                "execution_status": status.value,
                "duration_seconds": round(case_duration, 3),
                "emitted_findings_count": len(findings),
                "findings": [f.model_dump() for f in findings],
                "evaluation": case_eval.model_dump(),
                "telemetry": telemetry,
            }
        )

    total_duration = time.time() - start_total_time
    aggregate_metrics, _ = matcher.evaluate_batch(cases, predictions_by_case)

    output_payload = {
        "benchmark_run_metadata": {
            "configuration": "B",
            "configuration_name": "Configuration B — LLM-Only Code Auditor Baseline",
            "model_display_name": DEFAULT_CONFIG_B_PARAMS.display_name,
            "gateway_model_id": DEFAULT_CONFIG_B_PARAMS.gateway_model_id,
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_cases": len(cases),
            "total_duration_seconds": round(total_duration, 3),
            "execution_parameters": {
                "thinking_type": DEFAULT_CONFIG_B_PARAMS.thinking_type,
                "thinking_effort": DEFAULT_CONFIG_B_PARAMS.thinking_effort,
                "temperature": DEFAULT_CONFIG_B_PARAMS.temperature,
                "max_completion_tokens": DEFAULT_CONFIG_B_PARAMS.max_completion_tokens,
                "source_token_budget": DEFAULT_CONFIG_B_PARAMS.source_token_budget,
            },
            "tolerance_window": "+-10 lines",
            "cost_accounting": {
                "total_cost_usd": round(engine.cost_tracker.total_cost(), 4),
                "budget_ceiling_usd": DEFAULT_CONFIG_B_PARAMS.budget_ceiling_usd,
                "cost_per_input_million": DEFAULT_CONFIG_B_PARAMS.cost_per_input_million,
                "cost_per_output_million": DEFAULT_CONFIG_B_PARAMS.cost_per_output_million,
                "records_count": len(engine.cost_tracker.records),
            },
        },
        "aggregate_metrics": aggregate_metrics.model_dump(),
        "cases": case_records,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print("\n================================================================================")
    print("CONFIG B BENCHMARK EVALUATION RESULTS SUMMARY")
    print("================================================================================")
    print(f"Total Cases Evaluated:       {len(cases)}")
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
    print(f"Total Benchmark Cost:        ${engine.cost_tracker.total_cost():.4f} USD")
    print(f"Total Benchmark Latency:     {total_duration:.2f}s")
    print(f"Report Output File:          {output_file}")
    print("================================================================================\n")

    return output_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Config B Benchmark")
    parser.add_argument(
        "--output",
        type=Path,
        default=CONFIG_B_RESULTS_FILE,
        help="Destination JSON path",
    )
    args = parser.parse_args()
    run_benchmark(output_file=args.output)


if __name__ == "__main__":
    main()
