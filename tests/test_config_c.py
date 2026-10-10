"""Unit tests for Configuration C static findings formatting, capping, and prompt equivalence."""

from __future__ import annotations

from pathlib import Path

from auditor.llm.chunker import SourceChunk
from auditor.llm.prompt_builder import (
    build_config_c_user_prompt,
    build_user_prompt,
    get_system_prompt,
)
from auditor.llm.static_formatter import (
    filter_and_sort_static_findings,
    format_static_findings_section,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DERIVED_CONFIG_A = REPO_ROOT / "data" / "results" / "config_a_18_case_derived_run.json"


def _make_dummy_chunk(start_line: int, end_line: int, total_lines: int = 1000) -> SourceChunk:
    rendered = f"=== AUDIT TARGET: dummy.py (Lines {start_line} to {end_line} of {total_lines}) ===\n"
    for i in range(start_line, end_line + 1):
        rendered += f"{i}: pass\n"
    rendered += "=== END AUDIT TARGET ===\n"
    return SourceChunk(
        file_path="dummy.py",
        chunk_index=1,
        total_chunks=1,
        start_line=start_line,
        end_line=end_line,
        total_lines=total_lines,
        rendered_text=rendered,
        raw_code="pass\n",
        token_estimate=100,
        tier=1,
        scope_description="Dummy chunk",
    )


def test_chunk_intersection_filtering():
    """Verify that findings are filtered strictly by chunk boundary intersection."""
    chunk = _make_dummy_chunk(100, 200)
    findings = [
        {"finding_id": "f1", "start_line": 50, "end_line": 90},  # outside
        {"finding_id": "f2", "start_line": 95, "end_line": 105},  # intersects start
        {"finding_id": "f3", "start_line": 150, "end_line": 160},  # inside
        {"finding_id": "f4", "start_line": 195, "end_line": 210},  # intersects end
        {"finding_id": "f5", "start_line": 201, "end_line": 250},  # outside
    ]

    filtered = filter_and_sort_static_findings(findings, chunk)
    fids = [f["finding_id"] for f in filtered]
    assert fids == ["f2", "f3", "f4"]


def test_absolute_line_number_preservation_and_sorting():
    """Verify deterministic ascending sorting by start_line, then rule_id, then finding_id."""
    chunk = _make_dummy_chunk(1, 500)
    findings = [
        {"finding_id": "f_c", "start_line": 150, "end_line": 155, "provenance": {"rule_code": "S101"}},
        {"finding_id": "f_b", "start_line": 150, "end_line": 155, "provenance": {"rule_code": "B101"}},
        {"finding_id": "f_a", "start_line": 50, "end_line": 55, "provenance": {"rule_code": "S101"}},
    ]

    filtered = filter_and_sort_static_findings(findings, chunk)
    fids = [f["finding_id"] for f in filtered]
    # At line 50 comes first; at line 150, B101 comes before S101
    assert fids == ["f_a", "f_b", "f_c"]


def test_static_section_token_cap_and_omission_notice():
    """Verify that the 2,000-token cap enforces deterministic omission and includes the exact notice."""
    chunk = _make_dummy_chunk(1, 1000)
    # Generate 50 artificial findings
    findings = []
    for i in range(50):
        findings.append(
            {
                "finding_id": f"f_{i:02d}",
                "start_line": i * 10 + 1,
                "end_line": i * 10 + 5,
                "tool_name": "semgrep",
                "category_id": 2,
                "primary_cwe": "CWE-20",
                "description": "Very long description " * 20,
                "provenance": {"rule_id": f"rule_{i:02d}"},
            }
        )

    # Set tight budget of 500 tokens
    text, retained, omitted = format_static_findings_section(findings, chunk, token_budget=500)
    assert retained > 0
    assert omitted > 0
    assert retained + omitted == 50
    assert f"[Notice: {omitted} additional findings omitted]" in text


def test_config_c_prompt_equivalence_outside_static_section():
    """Verify that Config C user prompt is byte-for-byte identical to Config B user prompt outside static section."""
    chunk = _make_dummy_chunk(1, 100)
    b_prompt = build_user_prompt(chunk)

    # Case 1: Empty static section
    c_prompt_empty = build_config_c_user_prompt(chunk, static_section="")
    assert c_prompt_empty == b_prompt

    # Case 2: Injected static section
    static_section = "### DETECTED STATIC ANALYSIS FINDINGS (FOR REFERENCE ONLY)\n- Finding 1: ..."
    c_prompt_with_static = build_config_c_user_prompt(chunk, static_section=static_section)
    reconstructed_b = c_prompt_with_static.replace(f"\n{static_section.strip()}\n\n", "\n")
    assert reconstructed_b == b_prompt


def test_system_prompt_selection():
    """Verify system prompt retrieval for Config B and Config C."""
    sys_b = get_system_prompt(config="B")
    sys_c = get_system_prompt(config="C")
    assert "TAXONOMY OF DEFECTS" in sys_b
    assert "TAXONOMY OF DEFECTS" in sys_c
    assert sys_b == sys_c
