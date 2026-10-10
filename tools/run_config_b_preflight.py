#!/usr/bin/env python3
"""Execute Configuration B Preflight & Token Counting across all 18 Canonical Pilot Cases.

Adheres strictly to Phase 4A:
- Uses official /v1/messages/count_tokens endpoint.
- Renders all 18 cases / chunks using the frozen prompt and source protocol.
- Measures exact input tokens including system prompt, schema, headers, and line prefixes.
- Computes conservative cost upper bound using maximum output allowance (16,384 tokens) per request.
- Enforces $8.00 Config B allocation check.
- ZERO generation calls are issued.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditor.dataset.pilot_loader import load_pilot_cases_from_json
from auditor.dataset.source_resolver import extract_target_file_content, resolve_case_repo_path
from auditor.llm.chunker import SourceChunk, SourceChunker
from auditor.llm.config import DEFAULT_CONFIG_B_PARAMS
from auditor.llm.credentials import load_gateway_credentials
from auditor.llm.prompt_builder import build_user_prompt, get_system_prompt
from auditor.llm.token_counter import ApiTokenCounter
from auditor.models.ground_truth import BenchmarkCase


@dataclass
class CasePreflightRecord:
    case_id: str
    repository: str
    target_file: str
    total_lines: int
    tier: int
    num_chunks: int
    chunk_tokens: list[int]
    total_input_tokens: int
    max_output_tokens: int
    projected_max_cost_usd: float


def run_preflight() -> list[CasePreflightRecord]:
    print("================================================================================")
    print("PHASE 4A — CONFIGURATION B PREFLIGHT & OFFICIAL TOKEN COUNTING")
    print(f"Model: {DEFAULT_CONFIG_B_PARAMS.display_name} ({DEFAULT_CONFIG_B_PARAMS.gateway_model_id})")
    print(f"Thinking: {DEFAULT_CONFIG_B_PARAMS.thinking_type} | Effort: {DEFAULT_CONFIG_B_PARAMS.thinking_effort}")
    print(
        f"Source Budget: {DEFAULT_CONFIG_B_PARAMS.source_token_budget} tokens | Max Output: {DEFAULT_CONFIG_B_PARAMS.max_completion_tokens} tokens"
    )
    print(f"Config B Allocation Ceiling: ${DEFAULT_CONFIG_B_PARAMS.config_b_budget_usd:.2f} USD")
    print("Zero Generation Calls Policy: STRICTLY ENFORCED (count_tokens only)")
    print("================================================================================\n")

    # Load credentials safely
    creds = load_gateway_credentials()
    counter = ApiTokenCounter(creds, model_id=DEFAULT_CONFIG_B_PARAMS.gateway_model_id)

    # The chunker uses conservative local estimation for line interval grouping
    chunker = SourceChunker(token_budget=DEFAULT_CONFIG_B_PARAMS.source_token_budget)

    cases: list[BenchmarkCase] = load_pilot_cases_from_json(only_verified=True)
    system_prompt = get_system_prompt()

    records: list[CasePreflightRecord] = []
    total_all_input_tokens = 0
    total_all_chunks = 0
    total_projected_max_cost = 0.0

    print(
        f"{'Case ID':<10} | {'Repo':<22} | {'Lines':<6} | {'Tier':<5} | {'Chunks':<6} | {'Input Tokens':<13} | {'Max Cost ($)':<12}",
        flush=True,
    )
    print("-" * 88, flush=True)

    for case in cases:
        target_file = case.defects[0].file_path if case.defects else ""
        repo_path = resolve_case_repo_path(case)
        raw_source = extract_target_file_content(repo_path, case.commit_hash, target_file)
        lines_count = len(raw_source.splitlines())

        # Chunk using official token counting
        chunks: list[SourceChunk] = chunker.chunk_source(raw_source, target_file)

        chunk_tokens_list: list[int] = []
        for chunk in chunks:
            user_prompt = build_user_prompt(chunk)
            # Count complete request tokens (system + user prompt + thinking config)
            tokens = counter.count_tokens(
                user_content=user_prompt,
                system_prompt=system_prompt,
                thinking_type=DEFAULT_CONFIG_B_PARAMS.thinking_type,
                thinking_effort=DEFAULT_CONFIG_B_PARAMS.thinking_effort,
            )
            chunk_tokens_list.append(tokens)

        case_input_tokens = sum(chunk_tokens_list)
        case_chunks = len(chunks)
        max_output_for_case = case_chunks * DEFAULT_CONFIG_B_PARAMS.max_completion_tokens

        # Conservative pricing: $3/M input, $15/M output
        in_cost = (case_input_tokens / 1_000_000.0) * DEFAULT_CONFIG_B_PARAMS.cost_per_input_million
        out_max_cost = (max_output_for_case / 1_000_000.0) * DEFAULT_CONFIG_B_PARAMS.cost_per_output_million
        case_max_cost = in_cost + out_max_cost

        total_all_input_tokens += case_input_tokens
        total_all_chunks += case_chunks
        total_projected_max_cost += case_max_cost

        rec = CasePreflightRecord(
            case_id=case.case_id,
            repository=case.repository,
            target_file=target_file,
            total_lines=lines_count,
            tier=chunks[0].tier if chunks else 1,
            num_chunks=case_chunks,
            chunk_tokens=chunk_tokens_list,
            total_input_tokens=case_input_tokens,
            max_output_tokens=max_output_for_case,
            projected_max_cost_usd=round(case_max_cost, 4),
        )
        records.append(rec)

        print(
            f"{case.case_id:<10} | {case.repository:<22} | {lines_count:<6} | {rec.tier:<5} | {case_chunks:<6} | {case_input_tokens:<13} | ${case_max_cost:<11.4f}",
            flush=True,
        )

    print("-" * 88)
    print(f"Total Cases:                 {len(cases)}")
    print(f"Total Chunks:                {total_all_chunks}")
    print(f"Total Request Input Tokens:  {total_all_input_tokens:,}")
    print(f"Total Max Output Tokens:     {total_all_chunks * DEFAULT_CONFIG_B_PARAMS.max_completion_tokens:,}")
    print(f"Upper-Bound Projected Cost:  ${total_projected_max_cost:.4f} USD")
    print(f"Config B Budget Allocation:  ${DEFAULT_CONFIG_B_PARAMS.config_b_budget_usd:.2f} USD")

    if total_projected_max_cost > DEFAULT_CONFIG_B_PARAMS.config_b_budget_usd:
        print(
            f"\n[CRITICAL WARNING]: Upper-bound cost (${total_projected_max_cost:.4f}) exceeds Config B allocation (${DEFAULT_CONFIG_B_PARAMS.config_b_budget_usd:.2f})!"
        )
    else:
        print("\n[SUCCESS]: Conservative upper-bound fits safely within Config B allocation.")

    return records


if __name__ == "__main__":
    run_preflight()
