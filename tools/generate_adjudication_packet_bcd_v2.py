#!/usr/bin/env python3
"""Generate Human Adjudication Packet strictly across Configurations B, C, and D.

Version: 2.0 (Phase 5D Reconstructed Packet)
- Purely offline. Reads canonical ground truth and frozen Config B, C, D results.
- Excludes Config A entirely (B/C/D evaluation only).
- Groups by unique GT defect (each defect appears once with all matching configurations).
- Flags mechanical matching nuances (e.g. CAND-0007 Cat 2/CWE-400 review flag, CAND-0019 dist=1).
- Outputs to Project Documents/dataset/adjudication_packet_bcd_v2.json and markdown table.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from auditor.dataset.pilot_loader import load_pilot_cases_from_json
from auditor.models.ground_truth import BenchmarkCase

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_B_FILE = REPO_ROOT / "data" / "results" / "config_b_pilot_run.json"
CONFIG_C_FILE = REPO_ROOT / "data" / "results" / "config_c_pilot_run.json"
CONFIG_D_FILE = REPO_ROOT / "data" / "results" / "config_d_pilot_run.json"

OUTPUT_JSON = REPO_ROOT / "data" / "results" / "adjudication_packet_bcd_v2.json"
OUTPUT_MD = REPO_ROOT / "Project Documents" / "dataset" / "adjudication_packet_bcd_v2.md"


def generate_packet_v2() -> dict[str, Any]:
    pilot_cases: list[BenchmarkCase] = load_pilot_cases_from_json(only_verified=True)
    cases_dict = {c.case_id: c for c in pilot_cases}

    with open(CONFIG_B_FILE, encoding="utf-8") as f:
        b_data = json.load(f)
    with open(CONFIG_C_FILE, encoding="utf-8") as f:
        c_data = json.load(f)
    with open(CONFIG_D_FILE, encoding="utf-8") as f:
        d_data = json.load(f)

    cfg_runs = [
        ("Config B", b_data),
        ("Config C", c_data),
        ("Config D", d_data),
    ]
    # Collect all match pairs across B, C, D
    # Map: defect_id -> list of match records
    defect_matches: dict[str, list[dict[str, Any]]] = {}

    for cfg_label, run_data in cfg_runs:
        for c in run_data.get("cases", []):
            cid = c["case_id"]
            bcase = cases_dict[cid]
            mps = c.get("evaluation", {}).get("matched_pairs", [])

            for mp in mps:
                did = mp["defect_id"]
                fid = mp["finding_id"]
                gt_defect = next((d for d in bcase.defects if d.defect_id == did), None)
                finding_obj = next((f for f in c.get("findings", []) if f["finding_id"] == fid), None)

                if not gt_defect or not finding_obj:
                    continue

                # Verify distance
                gt_s, gt_e = gt_defect.start_line, gt_defect.end_line
                p_s, p_e = finding_obj["start_line"], finding_obj["end_line"]
                direct = not (p_e < gt_s or p_s > gt_e)
                if direct:
                    dist = 0
                elif p_e < gt_s:
                    dist = gt_s - p_e
                else:
                    dist = p_s - gt_e

                review_notes = []
                if cid == "CAND-0007":
                    review_notes.append(
                        "REVIEW FLAG: Finding reports JSON parsing DoS (CWE-400) at CSRF defect locus (CWE-352/20)"
                    )
                if not direct:
                    review_notes.append(f"Tolerance-only match: distance = {dist} lines (within ±10)")

                match_rec = {
                    "config": cfg_label,
                    "case_id": cid,
                    "defect_id": did,
                    "finding_id": fid,
                    "finding_file": finding_obj["file_path"],
                    "finding_lines": f"{p_s}-{p_e}",
                    "finding_title": finding_obj["title"],
                    "finding_description": finding_obj["description"],
                    "finding_cwe": finding_obj["primary_cwe"],
                    "finding_category": finding_obj.get("category_id"),
                    "matched_cwe": mp.get("matched_cwe"),
                    "is_direct_overlap": direct,
                    "distance_lines": dist,
                    "match_type": "Direct Overlap" if direct else f"Tolerance-Only (+{dist} lines)",
                    "review_notes": "; ".join(review_notes) if review_notes else "Clean direct match",
                }

                if did not in defect_matches:
                    defect_matches[did] = []
                defect_matches[did].append(match_rec)

    # Group by GT Defect
    grouped_defects: list[dict[str, Any]] = []
    for did in sorted(defect_matches.keys()):
        # Find which case it belongs to
        bcase = next(c for c in pilot_cases if any(d.defect_id == did for d in c.defects))
        gt_defect = next(d for d in bcase.defects if d.defect_id == did)
        matches = defect_matches[did]

        matching_cfgs = sorted(list(set(m["config"] for m in matches)))

        grouped_defects.append(
            {
                "defect_id": did,
                "case_id": bcase.case_id,
                "category_id": bcase.category_id if hasattr(bcase, "category_id") else gt_defect.category_id,
                "file_path": gt_defect.file_path,
                "gt_lines": f"{gt_defect.start_line}-{gt_defect.end_line}",
                "primary_cwe": gt_defect.primary_cwe,
                "acceptable_alternative_cwes": sorted(list(gt_defect.acceptable_alternative_cwes)),
                "gt_description": gt_defect.description,
                "matching_configurations": matching_cfgs,
                "matches_count": len(matches),
                "matches": matches,
            }
        )

    packet_data = {
        "metadata": {
            "title": "Human Adjudication Packet (Configurations B, C, D)",
            "version": "2.0 (Phase 5D Reconstructed)",
            "total_unique_gt_defects": len(grouped_defects),
            "total_matched_rows": sum(d["matches_count"] for d in grouped_defects),
            "config_counts": {
                "Config B": sum(1 for d in grouped_defects for m in d["matches"] if m["config"] == "Config B"),
                "Config C": sum(1 for d in grouped_defects for m in d["matches"] if m["config"] == "Config C"),
                "Config D": sum(1 for d in grouped_defects for m in d["matches"] if m["config"] == "Config D"),
            },
        },
        "grouped_defects": grouped_defects,
    }

    # Write JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(packet_data, f, indent=2)

    # Write Markdown
    md_lines = [
        "# Human Adjudication Packet — Configurations B, C, and D (Version 2.0)",
        "",
        "> Purpose: Forensic human root-cause adjudication of all mechanical true-positive detections across Configurations B, C, and D.",
        "> Note: Mechanical matches are not validated semantic discoveries until human adjudication.",
        "",
        f"- **Unique Ground-Truth Defects Represented:** {len(grouped_defects)}",
        f"- **Total Matched Rows:** {packet_data['metadata']['total_matched_rows']}",
        f"  - Config B: {packet_data['metadata']['config_counts']['Config B']}",
        f"  - Config C: {packet_data['metadata']['config_counts']['Config C']}",
        f"  - Config D: {packet_data['metadata']['config_counts']['Config D']}",
        "",
        "---",
        "",
    ]

    for item in grouped_defects:
        did = item["defect_id"]
        cid = item["case_id"]
        cat = item["category_id"]
        locus = f"{item['file_path']}:{item['gt_lines']}"
        cwes = f"{item['primary_cwe']} (alt: {item['acceptable_alternative_cwes']})"
        cfgs_str = ", ".join(item["matching_configurations"])

        md_lines.append(f"## {did} ({cid} — Category {cat})")
        md_lines.append(f"- **Target Locus:** `{locus}`")
        md_lines.append(f"- **CWE:** {cwes}")
        md_lines.append(f"- **Description:** {item['gt_description']}")
        md_lines.append(f"- **Matching Configurations ({len(item['matches'])}):** {cfgs_str}")
        md_lines.append("")
        md_lines.append(
            "| Config | Finding ID | Finding Lines | Match Type | Finding CWE | Finding Title | Notes / Flag |"
        )
        md_lines.append("| :--- | :--- | :---: | :--- | :---: | :--- | :--- |")

        for m in item["matches"]:
            md_lines.append(
                f"| {m['config']} | `{m['finding_id']}` | {m['finding_lines']} | {m['match_type']} | {m['finding_cwe']} | {m['finding_title'][:35]} | {m['review_notes']} |"
            )

        md_lines.append("")
        md_lines.append("### Adjudication Decision Table")
        md_lines.append(
            "| Configuration | Human Verdict (`ROOT_CAUSE_ALIGNED` / `PROXIMITY_ONLY` / `INDETERMINATE`) | Adjudicator Rationale |"
        )
        md_lines.append("| :--- | :--- | :--- |")
        for cfg in item["matching_configurations"]:
            md_lines.append(f"| {cfg} | `[PENDING]` | |")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    return packet_data


if __name__ == "__main__":
    pdata = generate_packet_v2()
    print("Generated Packet v2 successfully:")
    print(f"  Unique GT Defects: {pdata['metadata']['total_unique_gt_defects']}")
    print(f"  Total Matched Rows: {pdata['metadata']['total_matched_rows']}")
    print(f"  Config B: {pdata['metadata']['config_counts']['Config B']}")
    print(f"  Config C: {pdata['metadata']['config_counts']['Config C']}")
    print(f"  Config D: {pdata['metadata']['config_counts']['Config D']}")
    print(f"  Saved JSON to: {OUTPUT_JSON}")
    print(f"  Saved Markdown to: {OUTPUT_MD}")
