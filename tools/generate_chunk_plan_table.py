"""Inspect measured rendered-source tokens and compile canonical chunk plan."""

from __future__ import annotations

from auditor.dataset.pilot_loader import load_pilot_cases_from_json
from auditor.dataset.source_resolver import extract_target_file_content, resolve_case_repo_path
from auditor.llm.chunker import SourceChunker, render_source_lines
from auditor.llm.credentials import load_gateway_credentials
from auditor.llm.prompt_builder import get_system_prompt
from auditor.llm.token_counter import ApiTokenCounter


def main() -> None:
    cases = load_pilot_cases_from_json(only_verified=True)
    counter = ApiTokenCounter(load_gateway_credentials())
    sys_p = get_system_prompt()
    fallback_chunker = SourceChunker(token_budget=16000)

    print(
        f"{'Case ID':<10} | {'Repo':<22} | {'Lines':<6} | {'Tier':<5} | {'Chunks':<6} | "
        f"{'Rendered Src':<12} | {'Full-Req In':<12} | {'Max Cost ($)':<12} | {'Line Intervals'}"
    )
    print("-" * 120)

    total_chunks = 0
    total_rendered_tokens = 0
    total_full_request_tokens = 0
    total_max_cost = 0.0

    for c in cases:
        target_file = c.defects[0].file_path if c.defects else ""
        repo_p = resolve_case_repo_path(c)
        raw = extract_target_file_content(repo_p, c.commit_hash, target_file)
        lines = raw.splitlines(keepends=True)
        total_lines = len(lines)

        # 1. Render complete source file and measure tokens against B_source = 16,000
        full_rendered = render_source_lines(lines, 1, total_lines, target_file, total_lines)
        src_tokens = counter.count_tokens(full_rendered)

        if src_tokens <= 16000:
            # Tier 1 single-pass whole file
            tier = 1
            intervals = [(1, total_lines)]
            rendered_chunks = [full_rendered]
        else:
            # Multi-chunk using deterministic AST or windowing
            chunks = fallback_chunker.chunk_source(raw, target_file)
            tier = chunks[0].tier if chunks else 2
            intervals = [(ch.start_line, ch.end_line) for ch in chunks]
            rendered_chunks = [ch.rendered_text for ch in chunks]

        # Calculate full-request input tokens for all chunks of this case
        case_full_req_tokens = 0
        for r_text in rendered_chunks:
            usr_p = (
                f"Please perform a security and defect audit of the following Python source code:\n\n"
                f"{r_text}\n"
                f"Identify all concrete security vulnerabilities and functional logic defects in this code. "
                f"Return your audit results exclusively as a valid JSON object matching the required schema."
            )
            req_in = counter.count_tokens(usr_p, system_prompt=sys_p)
            case_full_req_tokens += req_in

        num_chunks = len(intervals)
        max_out_tokens = num_chunks * 16384
        case_max_cost = (case_full_req_tokens / 1_000_000.0) * 3.0 + (max_out_tokens / 1_000_000.0) * 15.0

        total_chunks += num_chunks
        total_rendered_tokens += src_tokens
        total_full_request_tokens += case_full_req_tokens
        total_max_cost += case_max_cost

        int_str = ", ".join(f"[{s}, {e}]" for s, e in intervals)
        print(
            f"{c.case_id:<10} | {c.repository:<22} | {total_lines:<6} | {tier:<5} | {num_chunks:<6} | "
            f"{src_tokens:<12} | {case_full_req_tokens:<12} | ${case_max_cost:<11.4f} | {int_str}"
        )

    print("-" * 120)
    print(f"Total Cases:                 {len(cases)}")
    print(f"Total Chunks:                {total_chunks}")
    print(f"Total Full-Request Input:    {total_full_request_tokens:,}")
    print(f"Total Max Output Allowance:  {total_chunks * 16384:,}")
    print(f"Upper-Bound Cost Estimate:   ${total_max_cost:.4f} USD")


if __name__ == "__main__":
    main()
