"""Analyze overlap between Config D findings, static findings, and retrieved context."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_A_DERIVED_FILE = REPO_ROOT / "data" / "results" / "config_a_18_case_derived_run.json"
CONFIG_D_RESULTS_FILE = REPO_ROOT / "data" / "results" / "config_d_pilot_run.json"


def analyze_config_d_overlap():
    with open(CONFIG_A_DERIVED_FILE, encoding="utf-8") as f:
        a_data = json.load(f)
    with open(CONFIG_D_RESULTS_FILE, encoding="utf-8") as f:
        d_data = json.load(f)

    static_by_case = {c["case_id"]: c["findings"] for c in a_data["cases"]}

    total_d_findings = 0
    total_overlapping_static = 0
    total_overlapping_context = 0
    total_overlapping_both = 0
    total_novel_findings = 0

    print("================================================================================")
    print("CONFIG D FINDING OVERLAP ANALYSIS (STATIC FINDINGS & RETRIEVED CONTEXT)")
    print("================================================================================")

    for case_d in d_data["cases"]:
        cid = case_d["case_id"]
        findings = case_d["findings"]
        s_findings = static_by_case.get(cid, [])
        chunk_telemetry = case_d.get("telemetry", {}).get("chunk_telemetry", [])

        # Gather all retrieved context excerpts across chunks for this case
        all_context_excerpts = []
        for ct in chunk_telemetry:
            for exc in ct.get("retrieved_excerpts", []):
                all_context_excerpts.append(exc)

        for df in findings:
            total_d_findings += 1
            d_start = df["start_line"]
            d_end = df["end_line"]

            # 1. Check overlap with static findings (+-10 lines on target file)
            has_static_overlap = False
            for sf in s_findings:
                s_start = sf["start_line"]
                s_end = sf["end_line"]
                line_dist = max(0, max(s_start, d_start) - min(s_end, d_end))
                if line_dist <= 10:
                    has_static_overlap = True
                    break

            # 2. Check overlap with context excerpts (whether finding references a symbol or file from retrieved context)
            # Note: Context excerpts are cross-file, but we check if finding mentions the context file or symbol
            has_context_overlap = False
            desc_text = (df.get("title", "") + " " + df.get("description", "")).lower()
            for exc in all_context_excerpts:
                sym = exc["symbol_name"].lower()
                cfile = exc["file_path"].lower()
                if (sym and sym in desc_text) or (cfile and cfile.split("/")[-1] in desc_text):
                    has_context_overlap = True
                    break

            if has_static_overlap and has_context_overlap:
                total_overlapping_both += 1
                total_overlapping_static += 1
                total_overlapping_context += 1
            elif has_static_overlap:
                total_overlapping_static += 1
            elif has_context_overlap:
                total_overlapping_context += 1
            else:
                total_novel_findings += 1

    print(f"Total Config D Findings Emitted:        {total_d_findings}")
    print(
        f"Findings Overlapping Static Findings:   {total_overlapping_static} ({total_overlapping_static / total_d_findings * 100:.1f}%)"
    )
    print(
        f"Findings Overlapping Context Excerpts:  {total_overlapping_context} ({total_overlapping_context / total_d_findings * 100:.1f}%)"
    )
    print(
        f"Findings Overlapping Both:              {total_overlapping_both} ({total_overlapping_both / total_d_findings * 100:.1f}%)"
    )
    print(
        f"Completely Novel / Independent Findings: {total_novel_findings} ({total_novel_findings / total_d_findings * 100:.1f}%)"
    )
    print("================================================================================")
    print("Note: Overlap is descriptive only and does not establish causality or guidance.")


if __name__ == "__main__":
    analyze_config_d_overlap()
