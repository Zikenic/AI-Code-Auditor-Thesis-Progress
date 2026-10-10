#!/usr/bin/env python3
"""Execute Configuration C Benchmark Run across all 18 Canonical Pilot Cases.

Adheres strictly to Phase 5A:
- Model: Claude Sonnet 4.6 (gateway ID: ag/claude-sonnet-4-6).
- Adaptive thinking with medium effort, temperature omitted.
- Max completion tokens: 16,384 tokens per chunk.
- Measured-source chunking under B_source = 16,000 tokens.
- Static findings section under B_static = 2,000 tokens per chunk.
- Just-in-time budget reservation against the $6.00 Config C budget.
- Fresh generation calls for every chunk (including CAND-0006).
- Retries transient errors (max 2 retries per chunk), each with its own reservation.
- FR-09 partial-run scoring discipline: stop_reason != end_turn or chunk failure discards case findings.
- Preserves raw responses, telemetry, and parsed predictions in data/results/config_c_pilot_run.json.
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
from auditor.llm.chunker import SourceChunk, SourceChunker
from auditor.llm.config import DEFAULT_CONFIG_C_PARAMS
from auditor.llm.cost_tracker import CostTracker
from auditor.llm.credentials import load_gateway_credentials
from auditor.llm.deduplication import deduplicate_findings
from auditor.llm.parser import ConfigBResponseParser
from auditor.llm.prompt_builder import (
    assert_zero_answer_leakage,
    build_config_c_user_prompt,
    get_system_prompt,
)
from auditor.llm.static_formatter import format_static_findings_section
from auditor.llm.token_counter import ApiTokenCounter
from auditor.matcher.engine import OfflineEvaluationMatcher
from auditor.models.finding import PredictedFinding
from auditor.models.ground_truth import BenchmarkCase
from auditor.models.result import AuditStatus

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO_ROOT / "data" / "results"
CONFIG_C_RESULTS_FILE = RESULTS_DIR / "config_c_pilot_run.json"
CONFIG_A_DERIVED_FILE = RESULTS_DIR / "config_a_18_case_derived_run.json"


def run_benchmark(output_file: Path = CONFIG_C_RESULTS_FILE) -> dict[str, Any]:
    print("================================================================================")
    print("CONFIGURATION C BENCHMARK EXECUTION — 18 CANONICAL PILOT CASES")
    print(f"Model: {DEFAULT_CONFIG_C_PARAMS.display_name} ({DEFAULT_CONFIG_C_PARAMS.gateway_model_id})")
    print(f"Thinking: {DEFAULT_CONFIG_C_PARAMS.thinking_type} | Effort: {DEFAULT_CONFIG_C_PARAMS.thinking_effort}")
    print(f"Max completion tokens: {DEFAULT_CONFIG_C_PARAMS.max_completion_tokens}")
    print(f"Config C Budget: ${DEFAULT_CONFIG_C_PARAMS.config_c_budget_usd:.2f} USD")
    print("================================================================================\n")

    creds = load_gateway_credentials()
    api_client = AnthropicApiClient(credentials=creds, timeout=300.0, max_retries=1)  # manual retry loop
    counter = ApiTokenCounter(creds, model_id=DEFAULT_CONFIG_C_PARAMS.gateway_model_id)
    chunker = SourceChunker(token_budget=DEFAULT_CONFIG_C_PARAMS.source_token_budget)
    cost_tracker = CostTracker(
        cost_per_input_million=DEFAULT_CONFIG_C_PARAMS.cost_per_input_million,
        cost_per_output_million=DEFAULT_CONFIG_C_PARAMS.cost_per_output_million,
        budget_ceiling_usd=DEFAULT_CONFIG_C_PARAMS.config_c_budget_usd,
    )
    parser = ConfigBResponseParser(model_name=DEFAULT_CONFIG_C_PARAMS.model_id)
    matcher = OfflineEvaluationMatcher(tolerance_lines=10)

    # Load frozen static findings
    with open(CONFIG_A_DERIVED_FILE, encoding="utf-8") as f:
        config_a_data = json.load(f)
    static_by_case = {c["case_id"]: c["findings"] for c in config_a_data["cases"]}

    cases: list[BenchmarkCase] = load_pilot_cases_from_json(only_verified=True)
    total_cases = len(cases)
    case_records: list[dict[str, Any]] = []
    predictions_by_case: dict[str, list[PredictedFinding]] = {}
    system_prompt = get_system_prompt(config="C")

    start_total_time = time.time()
    budget_exhausted = False

    for idx, case in enumerate(cases, 1):
        if budget_exhausted:
            print(f"[{idx}/{total_cases}] Skipping {case.case_id} due to budget exhaustion.")
            break

        target_file = case.defects[0].file_path if case.defects else ""
        repo_path = resolve_case_repo_path(case)
        raw_source = extract_target_file_content(repo_path, case.commit_hash, target_file)

        print(f"[{idx}/{total_cases}] Auditing {case.case_id} ({case.repository}) - {target_file}...", flush=True)

        chunks: list[SourceChunk] = chunker.chunk_source(raw_source, target_file)
        case_static_findings = static_by_case.get(case.case_id, [])

        # Leakage shield terms
        forbidden_terms = [case.commit_hash[:10]]
        for defect in case.defects:
            forbidden_terms.append(defect.defect_id)
            forbidden_terms.append(f"{target_file}:{defect.start_line}")

        case_findings: list[PredictedFinding] = []
        chunk_telemetry: list[dict[str, Any]] = []
        case_failed = False
        failure_reason = ""
        case_start = time.time()

        for chunk in chunks:
            # Format static section
            static_section, ret_count, omit_count = format_static_findings_section(
                findings=case_static_findings,
                chunk=chunk,
                token_budget=DEFAULT_CONFIG_C_PARAMS.static_token_budget,
                token_counter=counter.count_tokens,
            )
            user_prompt = build_config_c_user_prompt(chunk, static_section=static_section)
            assert_zero_answer_leakage(user_prompt, forbidden_terms)

            # Measure full input tokens for just-in-time reservation
            measured_input_toks = counter.count_tokens(
                user_content=user_prompt,
                system_prompt=system_prompt,
                thinking_type=DEFAULT_CONFIG_C_PARAMS.thinking_type,
                thinking_effort=DEFAULT_CONFIG_C_PARAMS.thinking_effort,
            )
            # Add gateway preamble overhead (3,000 tokens safety margin)
            reserved_in_toks = measured_input_toks + 3000
            reserved_out_toks = DEFAULT_CONFIG_C_PARAMS.max_completion_tokens

            # Just-in-time reservation check
            if cost_tracker.would_exceed_ceiling(
                reserved_prompt_tokens=reserved_in_toks,
                reserved_completion_tokens=reserved_out_toks,
            ):
                case_failed = True
                budget_exhausted = True
                failure_reason = (
                    f"Just-in-time budget reservation failed: call would exceed ${DEFAULT_CONFIG_C_PARAMS.config_c_budget_usd:.2f} ceiling "
                    f"(Spent: ${cost_tracker.total_cost():.4f})"
                )
                print(f"       [STOP]: {failure_reason}")
                break

            # Generation call with up to 2 retries for transient errors
            max_attempts = 3
            call_succeeded = False
            chunk_response_text = ""
            chunk_p_tokens = 0
            chunk_c_tokens = 0
            chunk_duration = 0.0
            last_err = ""
            attempt_count = 0

            for attempt in range(1, max_attempts + 1):
                attempt_count = attempt
                if attempt > 1:
                    # Retry requires fresh reservation check
                    if cost_tracker.would_exceed_ceiling(
                        reserved_prompt_tokens=reserved_in_toks,
                        reserved_completion_tokens=reserved_out_toks,
                    ):
                        case_failed = True
                        budget_exhausted = True
                        failure_reason = f"Budget ceiling exceeded before retry attempt {attempt}"
                        break
                    print(f"       Retrying chunk {chunk.chunk_index} (attempt {attempt})...")
                    time.sleep(2**attempt * 2)

                c_start = time.time()
                try:
                    chunk_response_text, chunk_p_tokens, chunk_c_tokens = api_client.generate(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        max_tokens=DEFAULT_CONFIG_C_PARAMS.max_completion_tokens,
                        model_id=DEFAULT_CONFIG_C_PARAMS.gateway_model_id,
                        thinking_type=DEFAULT_CONFIG_C_PARAMS.thinking_type,
                        thinking_effort=DEFAULT_CONFIG_C_PARAMS.thinking_effort,
                    )
                    chunk_duration = time.time() - c_start
                    call_succeeded = True
                    break
                except Exception as e:
                    chunk_duration = time.time() - c_start
                    last_err = str(e)
                    print(f"       Attempt {attempt} failed on chunk {chunk.chunk_index}: {last_err}")

            if not call_succeeded:
                case_failed = True
                failure_reason = f"Chunk {chunk.chunk_index} failed after {attempt_count} attempts: {last_err}"
                break

            # Record actual cost
            cost_rec = cost_tracker.record_usage(
                case_id=case.case_id,
                chunk_index=chunk.chunk_index,
                prompt_tokens=chunk_p_tokens,
                completion_tokens=chunk_c_tokens,
                duration_seconds=chunk_duration,
                model_id=DEFAULT_CONFIG_C_PARAMS.model_id,
            )

            # Record chunk telemetry including raw response
            chunk_telemetry.append(
                {
                    "chunk_index": chunk.chunk_index,
                    "tokens": {"prompt": chunk_p_tokens, "completion": chunk_c_tokens},
                    "cost_usd": cost_rec.cost_usd,
                    "duration_seconds": round(chunk_duration, 3),
                    "raw_response": chunk_response_text,
                    "attempts": attempt_count,
                    "static_findings_retained": ret_count,
                    "static_findings_omitted": omit_count,
                }
            )

            # Parse chunk findings
            try:
                parsed_findings = parser.parse_response(
                    raw_text=chunk_response_text,
                    expected_file_path=target_file,
                    total_file_lines=chunk.total_lines,
                    chunk_start_line=chunk.start_line,
                    chunk_end_line=chunk.end_line,
                )
                case_findings.extend(parsed_findings)
            except Exception as e:
                case_failed = True
                failure_reason = f"Parsing failed on chunk {chunk.chunk_index}: {str(e)}"
                break

        case_duration = time.time() - case_start

        # FR-09 Partial-run scoring discipline
        if case_failed:
            status = AuditStatus.FAILED
            final_case_findings = []
        else:
            status = AuditStatus.SUCCESS
            final_case_findings = deduplicate_findings(case_findings)

        predictions_by_case[case.case_id] = final_case_findings
        case_eval = matcher.evaluate_case(case, final_case_findings)

        spent_so_far = cost_tracker.total_cost()
        chunks_count = len(chunks)
        tier_used = chunks[0].tier if chunks else 1

        print(
            f"       Status: {status.value} | Chunks: {chunks_count} (Tier {tier_used}) | "
            f"Findings: {len(final_case_findings)} | TP: {case_eval.true_positives} | FP: {case_eval.false_positives} | "
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
                "failure_reason": failure_reason if case_failed else None,
                "duration_seconds": round(case_duration, 3),
                "emitted_findings_count": len(final_case_findings),
                "findings": [f.model_dump() for f in final_case_findings],
                "evaluation": case_eval.model_dump(),
                "telemetry": {
                    "total_chunks": chunks_count,
                    "tier_used": tier_used,
                    "raw_findings_count": len(case_findings),
                    "deduplicated_findings_count": len(final_case_findings),
                    "total_duration_seconds": round(case_duration, 3),
                    "chunk_telemetry": chunk_telemetry,
                },
            }
        )

    total_duration = time.time() - start_total_time
    aggregate_metrics, _ = matcher.evaluate_batch(cases, predictions_by_case)

    output_payload = {
        "benchmark_run_metadata": {
            "configuration": "C",
            "configuration_name": "Configuration C — Static-Augmented Heuristic LLM Review",
            "model_display_name": DEFAULT_CONFIG_C_PARAMS.display_name,
            "gateway_model_id": DEFAULT_CONFIG_C_PARAMS.gateway_model_id,
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_cases_evaluated": len(case_records),
            "total_canonical_cases": len(cases),
            "is_complete_run": len(case_records) == len(cases) and not budget_exhausted,
            "total_duration_seconds": round(total_duration, 3),
            "execution_parameters": {
                "thinking_type": DEFAULT_CONFIG_C_PARAMS.thinking_type,
                "thinking_effort": DEFAULT_CONFIG_C_PARAMS.thinking_effort,
                "temperature": DEFAULT_CONFIG_C_PARAMS.temperature,
                "max_completion_tokens": DEFAULT_CONFIG_C_PARAMS.max_completion_tokens,
                "source_token_budget": DEFAULT_CONFIG_C_PARAMS.source_token_budget,
                "static_token_budget": DEFAULT_CONFIG_C_PARAMS.static_token_budget,
            },
            "tolerance_window": "+-10 lines",
            "cost_accounting": {
                "total_cost_usd": round(cost_tracker.total_cost(), 4),
                "budget_ceiling_usd": DEFAULT_CONFIG_C_PARAMS.config_c_budget_usd,
                "cost_per_input_million": DEFAULT_CONFIG_C_PARAMS.cost_per_input_million,
                "cost_per_output_million": DEFAULT_CONFIG_C_PARAMS.cost_per_output_million,
                "records_count": len(cost_tracker.records),
            },
        },
        "aggregate_metrics": aggregate_metrics.model_dump(),
        "cases": case_records,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print("\n================================================================================")
    print("CONFIG C BENCHMARK EVALUATION RESULTS SUMMARY")
    print("================================================================================")
    print(f"Total Cases Evaluated:       {len(case_records)} / {len(cases)}")
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
    print(f"Total Benchmark Cost:        ${cost_tracker.total_cost():.4f} USD")
    print(f"Total Benchmark Latency:     {total_duration:.2f}s")
    print(f"Report Output File:          {output_file}")
    print("================================================================================\n")

    return output_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Config C Benchmark")
    parser.add_argument(
        "--output",
        type=Path,
        default=CONFIG_C_RESULTS_FILE,
        help="Destination JSON path",
    )
    args = parser.parse_args()
    run_benchmark(output_file=args.output)


if __name__ == "__main__":
    main()
