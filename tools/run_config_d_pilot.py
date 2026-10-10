#!/usr/bin/env python3
"""Execute Configuration D Benchmark Run across all 18 Canonical Pilot Cases.

Adheres strictly to Phase 5B:
- Model: Claude Sonnet 4.6 (gateway ID: ag/claude-sonnet-4-6).
- Adaptive thinking with medium effort, temperature omitted.
- Max completion tokens: 16,384 tokens per chunk.
- Measured-source chunking under B_source = 16,000 tokens.
- Static findings section under B_static = 2,000 tokens per chunk.
- Repository context section under B_context = 4,000 tokens per chunk (Option B: AST + Lexical).
- Pre-fix git tree indexing exclusively (INV-10).
- Strict zero answer leakage guard (INV-09).
- Just-in-time budget reservation against the $6.00 Config D budget.
- Fresh generation calls for every chunk.
- Retries transient errors (max 2 retries per chunk), each with its own reservation.
- FR-09 partial-run scoring discipline: stop_reason != end_turn or chunk failure discards case findings.
- Preserves raw responses, telemetry, and parsed predictions in data/results/config_d_pilot_run.json.
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
from auditor.llm.config import DEFAULT_CONFIG_D_PARAMS
from auditor.llm.context_retriever import RepositoryContextRetriever, RepositoryIndex
from auditor.llm.cost_tracker import CostTracker
from auditor.llm.credentials import load_gateway_credentials
from auditor.llm.deduplication import deduplicate_findings
from auditor.llm.parser import ConfigBResponseParser
from auditor.llm.prompt_builder import (
    assert_zero_answer_leakage,
    build_config_d_user_prompt,
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
CONFIG_D_RESULTS_FILE = RESULTS_DIR / "config_d_pilot_run.json"
CONFIG_A_DERIVED_FILE = RESULTS_DIR / "config_a_18_case_derived_run.json"


def run_benchmark(output_file: Path = CONFIG_D_RESULTS_FILE) -> dict[str, Any]:
    print("================================================================================")
    print("CONFIGURATION D BENCHMARK EXECUTION — 18 CANONICAL PILOT CASES")
    print(f"Model: {DEFAULT_CONFIG_D_PARAMS.display_name} ({DEFAULT_CONFIG_D_PARAMS.gateway_model_id})")
    print(f"Thinking: {DEFAULT_CONFIG_D_PARAMS.thinking_type} | Effort: {DEFAULT_CONFIG_D_PARAMS.thinking_effort}")
    print(f"Max completion tokens: {DEFAULT_CONFIG_D_PARAMS.max_completion_tokens}")
    print(
        f"Budgets: Source={DEFAULT_CONFIG_D_PARAMS.source_token_budget} | Static={DEFAULT_CONFIG_D_PARAMS.static_token_budget} | Context={DEFAULT_CONFIG_D_PARAMS.context_token_budget}"
    )
    print(f"Config D Budget: ${DEFAULT_CONFIG_D_PARAMS.config_d_budget_usd:.2f} USD")
    print("================================================================================\n", flush=True)

    # 1. Setup credentials and clients
    creds = load_gateway_credentials()
    api_client = AnthropicApiClient(credentials=creds)
    token_counter = ApiTokenCounter(credentials=creds, model_id=DEFAULT_CONFIG_D_PARAMS.gateway_model_id)
    cost_tracker = CostTracker(budget_ceiling_usd=DEFAULT_CONFIG_D_PARAMS.config_d_budget_usd)
    parser = ConfigBResponseParser()
    chunker = SourceChunker(token_budget=DEFAULT_CONFIG_D_PARAMS.source_token_budget)
    matcher = OfflineEvaluationMatcher(tolerance_lines=10)

    # 2. Load frozen static findings from derived 18-case run
    with open(CONFIG_A_DERIVED_FILE, encoding="utf-8") as f:
        config_a_data = json.load(f)
    static_by_case = {c["case_id"]: c["findings"] for c in config_a_data["cases"]}

    # 3. Load 18 canonical pilot cases
    cases: list[BenchmarkCase] = load_pilot_cases_from_json(only_verified=True)
    system_prompt = get_system_prompt(config="D")

    # In-memory index cache
    repo_indices: dict[str, RepositoryIndex] = {}

    case_results: list[dict[str, Any]] = []
    predictions_by_case: dict[str, list[PredictedFinding]] = {}
    total_start_time = time.time()
    budget_exhausted = False

    for case_idx, case in enumerate(cases, 1):
        if budget_exhausted:
            print(f"\n[SKIP]: Skipping remaining cases due to budget exhaustion ({case.case_id})")
            break

        cat_id = case.defects[0].category_id if case.defects else 0
        print(
            f"\n[{case_idx}/18] Auditing Case: {case.case_id} ({case.repository}) — Category {cat_id}",
            flush=True,
        )
        case_start = time.time()
        target_file = case.defects[0].file_path if case.defects else ""
        repo_path = resolve_case_repo_path(case)

        # Index pre-fix repo if not cached
        idx_key = f"{case.repository}:{case.commit_hash}"
        if idx_key not in repo_indices:
            print(f"  Building pre-fix index for {case.repository} at {case.commit_hash[:8]}...", flush=True)
            t_idx = time.time()
            repo_indices[idx_key] = RepositoryIndex(repo_dir=repo_path, commit_hash=case.commit_hash)
            print(
                f"    Indexed {len(repo_indices[idx_key].files)} files, {len(repo_indices[idx_key].symbol_table)} symbols in {time.time() - t_idx:.2f}s.",
                flush=True,
            )

        retriever = RepositoryContextRetriever(repo_indices[idx_key])

        raw_source = extract_target_file_content(repo_path, case.commit_hash, target_file)
        chunks: list[SourceChunk] = chunker.chunk_source(raw_source, target_file)
        print(f"  Source chunks: {len(chunks)} | Target file: {target_file}", flush=True)

        case_static_findings = static_by_case.get(case.case_id, [])

        case_findings: list[PredictedFinding] = []
        chunk_telemetry: list[dict[str, Any]] = []
        case_failed = False
        failure_reason = ""

        # Forbidden terms for zero answer leakage assertion
        forbidden_terms = [
            case.commit_hash[:8],
            target_file.split("/")[-1].replace(".py", "") + "_fix",
        ]
        for defect in case.defects:
            forbidden_terms.append(defect.defect_id)
            forbidden_terms.append(f"{target_file}:{defect.start_line}")

        for chunk in chunks:
            print(
                f"  -> Processing Chunk {chunk.chunk_index}/{chunk.total_chunks} (Lines {chunk.start_line}..{chunk.end_line})",
                flush=True,
            )

            # Format static section
            static_section, ret_count, omit_count = format_static_findings_section(
                findings=case_static_findings,
                chunk=chunk,
                token_budget=DEFAULT_CONFIG_D_PARAMS.static_token_budget,
                token_counter=token_counter.count_tokens,
            )

            # Retrieve repository context
            t_ret = time.time()
            context_section, context_items, omitted_context = retriever.retrieve_context(
                target_file=target_file,
                chunk_start=chunk.start_line,
                chunk_end=chunk.end_line,
                chunk_code=chunk.raw_code,
                max_tokens=DEFAULT_CONFIG_D_PARAMS.context_token_budget,
            )
            ret_duration = time.time() - t_ret

            # Assemble full Config D prompt
            user_prompt = build_config_d_user_prompt(
                chunk,
                static_section=static_section,
                context_section=context_section,
            )

            # INV-09 Zero answer leakage check
            assert_zero_answer_leakage(user_prompt, forbidden_terms)

            # Token counting preflight for this request
            count_in_toks = token_counter.count_tokens(
                user_content=user_prompt,
                system_prompt=system_prompt,
                thinking_type=DEFAULT_CONFIG_D_PARAMS.thinking_type,
                thinking_effort=DEFAULT_CONFIG_D_PARAMS.thinking_effort,
            )
            reserved_in_toks = count_in_toks + 3000
            reserved_out_toks = DEFAULT_CONFIG_D_PARAMS.max_completion_tokens

            # Just-in-time reservation check against remaining budget
            if cost_tracker.would_exceed_ceiling(
                reserved_prompt_tokens=reserved_in_toks,
                reserved_completion_tokens=reserved_out_toks,
            ):
                case_failed = True
                budget_exhausted = True
                failure_reason = (
                    f"Just-in-time budget reservation failed: call would exceed ${DEFAULT_CONFIG_D_PARAMS.config_d_budget_usd:.2f} ceiling "
                    f"(Spent: ${cost_tracker.total_cost():.4f})"
                )
                print(f"       [STOP]: {failure_reason}", flush=True)
                break

            # Generation call with up to 2 retries
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
                    if cost_tracker.would_exceed_ceiling(
                        reserved_prompt_tokens=reserved_in_toks,
                        reserved_completion_tokens=reserved_out_toks,
                    ):
                        case_failed = True
                        budget_exhausted = True
                        failure_reason = f"Budget ceiling exceeded before retry attempt {attempt}"
                        break
                    print(f"       Retrying chunk {chunk.chunk_index} (attempt {attempt})...", flush=True)
                    time.sleep(2**attempt * 2)

                c_start = time.time()
                try:
                    chunk_response_text, chunk_p_tokens, chunk_c_tokens = api_client.generate(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        max_tokens=DEFAULT_CONFIG_D_PARAMS.max_completion_tokens,
                        model_id=DEFAULT_CONFIG_D_PARAMS.gateway_model_id,
                        thinking_type=DEFAULT_CONFIG_D_PARAMS.thinking_type,
                        thinking_effort=DEFAULT_CONFIG_D_PARAMS.thinking_effort,
                    )
                    chunk_duration = time.time() - c_start
                    call_succeeded = True
                    break
                except Exception as e:
                    chunk_duration = time.time() - c_start
                    last_err = str(e)
                    print(f"       Attempt {attempt} failed on chunk {chunk.chunk_index}: {last_err}", flush=True)

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
                model_id=DEFAULT_CONFIG_D_PARAMS.model_id,
            )

            # Save raw response and retrieval telemetry before parsing
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
                    "retrieved_context_items_count": len(context_items),
                    "retrieved_context_omitted_count": omitted_context,
                    "retrieval_duration_seconds": round(ret_duration, 3),
                    "retrieved_excerpts": [
                        {
                            "file_path": it.file_path,
                            "start_line": it.start_line,
                            "end_line": it.end_line,
                            "symbol_name": it.symbol_name,
                            "priority": it.priority,
                        }
                        for it in context_items
                    ],
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
        print(
            f"  Case Status: [{status.value.upper()}] | Findings: {len(final_case_findings)} | "
            f"TP={case_eval.true_positives} FP={case_eval.false_positives} FN={case_eval.false_negatives} | "
            f"Latency: {case_duration:.2f}s | Spent: ${spent_so_far:.4f}",
            flush=True,
        )

        case_record = {
            "case_id": case.case_id,
            "repository": case.repository,
            "commit_hash": case.commit_hash,
            "target_file": target_file,
            "category_id": case.defects[0].category_id if case.defects else 0,
            "primary_cwe": case.defects[0].primary_cwe if case.defects else "CWE-UNKNOWN",
            "gt_loci": [[d.start_line, d.end_line] for d in case.defects],
            "execution_status": status.value,
            "failure_reason": failure_reason if case_failed else None,
            "duration_seconds": round(case_duration, 2),
            "emitted_findings_count": len(final_case_findings),
            "findings": [f.model_dump() for f in final_case_findings],
            "evaluation": case_eval.model_dump(),
            "telemetry": {
                "chunk_telemetry": chunk_telemetry,
                "total_prompt_tokens": sum(ct["tokens"]["prompt"] for ct in chunk_telemetry),
                "total_completion_tokens": sum(ct["tokens"]["completion"] for ct in chunk_telemetry),
                "total_cost_usd": sum(ct["cost_usd"] for ct in chunk_telemetry),
            },
        }
        case_results.append(case_record)

    total_duration = time.time() - total_start_time

    # Calculate aggregate benchmark metrics
    all_evals = [cr["evaluation"] for cr in case_results]
    agg_tp = sum(e["true_positives"] for e in all_evals)
    agg_fp = sum(e["false_positives"] for e in all_evals)
    agg_fn = sum(e["false_negatives"] for e in all_evals)

    precision = (agg_tp / (agg_tp + agg_fp)) * 100.0 if (agg_tp + agg_fp) > 0 else 0.0
    recall = (agg_tp / (agg_tp + agg_fn)) * 100.0 if (agg_tp + agg_fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    output_payload = {
        "metadata": {
            "configuration": "D",
            "configuration_name": "Full Hybrid Review (Static Analysis + Repository Context)",
            "model_id": DEFAULT_CONFIG_D_PARAMS.model_id,
            "gateway_model_id": DEFAULT_CONFIG_D_PARAMS.gateway_model_id,
            "thinking_type": DEFAULT_CONFIG_D_PARAMS.thinking_type,
            "thinking_effort": DEFAULT_CONFIG_D_PARAMS.thinking_effort,
            "source_budget_tokens": DEFAULT_CONFIG_D_PARAMS.source_token_budget,
            "static_budget_tokens": DEFAULT_CONFIG_D_PARAMS.static_token_budget,
            "context_budget_tokens": DEFAULT_CONFIG_D_PARAMS.context_token_budget,
            "budget_ceiling_usd": DEFAULT_CONFIG_D_PARAMS.config_d_budget_usd,
            "total_cost_usd": cost_tracker.total_cost(),
            "total_duration_seconds": round(total_duration, 2),
            "total_cases_evaluated": len(case_results),
            "aggregate_metrics": {
                "true_positives": agg_tp,
                "false_positives": agg_fp,
                "false_negatives": agg_fn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
            },
        },
        "cases": case_results,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print("\n================================================================================")
    print("CONFIGURATION D BENCHMARK COMPLETE")
    print(f"Artifact Saved: {output_file}")
    print(f"Total Cases:    {len(case_results)}/18")
    print(f"Total Latency:  {total_duration:.2f}s")
    print(f"Total Spend:    ${cost_tracker.total_cost():.4f} USD")
    print(f"Aggregates:     TP={agg_tp} | FP={agg_fp} | FN={agg_fn}")
    print(f"Precision:      {precision:.2f}% | Recall: {recall:.2f}% | F1: {f1:.2f}%")
    print("================================================================================")

    return output_payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Configuration D Benchmark Pilot.")
    parser.add_argument("--output", type=Path, default=CONFIG_D_RESULTS_FILE, help="Path for results artifact.")
    args = parser.parse_args()
    run_benchmark(output_file=args.output)
