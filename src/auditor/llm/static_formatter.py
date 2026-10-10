"""Static findings formatting, chunk-intersection filtering, and token-capping for Configuration C.

Adheres strictly to Phase 5A:
- Intersecting findings only (max(chunk_start, f_start) <= min(chunk_end, f_end))
- Deterministic sorting: start_line ascending, then rule_id ascending, then finding_id
- Deterministic token cap: B_static = 2,000 tokens
- Omission notice: 'N additional findings omitted'
- Neutral, non-leading prompt language
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from auditor.llm.chunker import SourceChunk, default_token_estimator


def extract_finding_fields(finding: dict[str, Any]) -> tuple[str, str, int, int, str, str, str, str]:
    """Extract normalized fields for a static finding dictionary.

    Returns: (finding_id, tool_name, start_line, end_line, rule_id, category_str, cwe_str, message)
    """
    fid = finding.get("finding_id", "")
    prov = finding.get("provenance") or {}
    tool = finding.get("tool_name") or prov.get("tool") or "static_tool"
    start_line = int(finding.get("start_line", 0))
    end_line = int(finding.get("end_line", 0))

    rule_raw = prov.get("rule_code") or prov.get("rule_id") or prov.get("check_id") or "unmapped_rule"
    rule_str = str(rule_raw)
    if "rules.semgrep." in rule_str:
        rule_id = rule_str.split("rules.semgrep.")[-1]
    else:
        rule_id = rule_str

    cat_id = finding.get("category_id")
    cat_str = f"Category {cat_id}" if cat_id is not None else "unmapped"
    cwe_str = finding.get("primary_cwe") or "unmapped"
    msg = finding.get("description") or finding.get("title") or ""

    return fid, tool, start_line, end_line, rule_id, cat_str, cwe_str, msg


def filter_and_sort_static_findings(
    findings: list[dict[str, Any]],
    chunk: SourceChunk,
) -> list[dict[str, Any]]:
    """Filter findings intersecting the chunk line range and sort deterministically."""
    intersecting: list[dict[str, Any]] = []
    for f in findings:
        f_start = int(f.get("start_line", 0))
        f_end = int(f.get("end_line", 0))
        if max(chunk.start_line, f_start) <= min(chunk.end_line, f_end):
            intersecting.append(f)

    def sort_key(item: dict[str, Any]) -> tuple[int, str, str]:
        fid, _, s_line, _, r_id, _, _, _ = extract_finding_fields(item)
        return (s_line, r_id, fid)

    return sorted(intersecting, key=sort_key)


def render_single_finding_entry(index: int, item: dict[str, Any]) -> str:
    """Render a single formatted finding item."""
    _, tool, s_line, e_line, rule_id, cat_str, cwe_str, msg = extract_finding_fields(item)
    return (
        f"- Finding {index}: [{tool}] Rule: {rule_id} | Lines: {s_line}-{e_line} | Mapped: {cat_str} ({cwe_str})\n"
        f"  Message: {msg}\n"
    )


def format_static_findings_section(
    findings: list[dict[str, Any]],
    chunk: SourceChunk,
    token_budget: int = 2000,
    token_counter: Callable[[str], int] | None = None,
) -> tuple[str, int, int]:
    """Format and cap the static findings section for a chunk.

    Returns:
        (rendered_section_text, retained_count, omitted_count)
    """
    sorted_findings = filter_and_sort_static_findings(findings, chunk)
    if not sorted_findings:
        return "", 0, 0

    count_tokens = token_counter or default_token_estimator

    header = (
        "### DETECTED STATIC ANALYSIS FINDINGS (FOR REFERENCE ONLY)\n"
        "The following automated static analysis findings were flagged by baseline static analyzers (Ruff / Semgrep) "
        "for lines within this code chunk:\n\n"
    )
    disclaimer = (
        "\nNote: The findings above are automated tool outputs provided strictly for informational reference. "
        "They may contain false positives, irrelevant warnings, or incomplete diagnostics. Please conduct your "
        "own rigorous, independent code review of the source code and decide independently whether to corroborate, "
        "refine, or disregard any of these tool findings.\n"
    )

    total_avail = len(sorted_findings)
    retained_items: list[dict[str, Any]] = []

    for item in sorted_findings:
        cand_retained = retained_items + [item]
        cand_omitted = total_avail - len(cand_retained)

        # Build candidate text
        body_lines = [render_single_finding_entry(i + 1, it) for i, it in enumerate(cand_retained)]
        cand_text = header + "".join(body_lines)
        if cand_omitted > 0:
            cand_text += f"\n[Notice: {cand_omitted} additional findings omitted]\n"
        cand_text += disclaimer

        if count_tokens(cand_text) <= token_budget:
            retained_items = cand_retained
        else:
            break

    # If capping occurred or even initial header+disclaimer exceeds budget
    omitted_count = total_avail - len(retained_items)

    # In case adding omission notice caused an overflow, deterministically back off
    while retained_items:
        body_lines = [render_single_finding_entry(i + 1, it) for i, it in enumerate(retained_items)]
        full_text = header + "".join(body_lines)
        if omitted_count > 0:
            full_text += f"\n[Notice: {omitted_count} additional findings omitted]\n"
        full_text += disclaimer

        if count_tokens(full_text) <= token_budget:
            return full_text, len(retained_items), omitted_count

        retained_items.pop()
        omitted_count = total_avail - len(retained_items)

    # Extreme edge case: header + notice + disclaimer cannot fit 2,000 tokens
    if count_tokens(header + f"\n[Notice: {total_avail} additional findings omitted]\n" + disclaimer) <= token_budget:
        return header + f"\n[Notice: {total_avail} additional findings omitted]\n" + disclaimer, 0, total_avail

    return "", 0, total_avail
