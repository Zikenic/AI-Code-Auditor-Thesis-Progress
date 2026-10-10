"""Generate Human Adjudication Packet across Config B, Config C, and Config D."""

from __future__ import annotations

import json
from pathlib import Path

from auditor.dataset.pilot_loader import load_pilot_cases_from_json
from auditor.models.ground_truth import BenchmarkCase

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_B_FILE = REPO_ROOT / "data" / "results" / "config_b_pilot_run.json"
CONFIG_C_FILE = REPO_ROOT / "data" / "results" / "config_c_pilot_run.json"
CONFIG_D_FILE = REPO_ROOT / "data" / "results" / "config_d_pilot_run.json"


def generate_adjudication_packet():
    cases_dict: dict[str, BenchmarkCase] = {c.case_id: c for c in load_pilot_cases_from_json(only_verified=True)}

    with open(CONFIG_B_FILE, encoding="utf-8") as f:
        b_data = json.load(f)
    with open(CONFIG_C_FILE, encoding="utf-8") as f:
        c_data = json.load(f)
    with open(CONFIG_D_FILE, encoding="utf-8") as f:
        d_data = json.load(f)

    rows = []

    for cfg_label, cfg_data in [("Config B", b_data), ("Config C", c_data), ("Config D", d_data)]:
        for c in cfg_data["cases"]:
            cid = c["case_id"]
            bench_case = cases_dict[cid]
            eval_info = c["evaluation"]

            for pair in eval_info.get("matched_pairs", []):
                fid = pair["finding_id"]
                did = pair["defect_id"]
                is_direct = pair["is_direct_overlap"]

                # Find defect object
                gt_defect = next((d for d in bench_case.defects if d.defect_id == did), None)
                # Find finding object
                finding_obj = next((f for f in c["findings"] if f["finding_id"] == fid), None)

                rows.append(
                    {
                        "config": cfg_label,
                        "case_id": cid,
                        "defect_id": did,
                        "gt_file": gt_defect.file_path if gt_defect else "",
                        "gt_locus": f"{gt_defect.start_line}-{gt_defect.end_line}" if gt_defect else "",
                        "gt_desc": gt_defect.description if gt_defect else "",
                        "finding_id": fid,
                        "finding_file": finding_obj["file_path"] if finding_obj else "",
                        "finding_lines": f"{finding_obj['start_line']}-{finding_obj['end_line']}"
                        if finding_obj
                        else "",
                        "finding_title": finding_obj["title"] if finding_obj else "",
                        "finding_desc": finding_obj["description"] if finding_obj else "",
                        "match_type": "Direct Overlap" if is_direct else "Tolerance-Only (±10)",
                    }
                )

    print("================================================================================")
    print("HUMAN ADJUDICATION PACKET — ALL MECHANICAL TRUE POSITIVES (B, C, D)")
    print("================================================================================\n")

    print(
        f"| {'Config':<8} | {'Case ID':<9} | {'Defect ID':<15} | {'GT Locus':<10} | {'Finding Lines':<13} | {'Match Type':<18} | {'Finding Title':<40} |"
    )
    print(f"|{'-' * 10}|{'-' * 11}|{'-' * 17}|{'-' * 12}|{'-' * 15}|{'-' * 20}|{'-' * 42}|")

    for r in rows:
        flag = " [REVIEW FLAG: Cat 2/CWE-400]" if r["case_id"] == "CAND-0007" else ""
        title = (r["finding_title"][:38] + "..") if len(r["finding_title"]) > 40 else r["finding_title"]
        print(
            f"| {r['config']:<8} | {r['case_id']:<9} | {r['defect_id']:<15} | {r['gt_locus']:<10} | {r['finding_lines']:<13} | {r['match_type']:<18} | {title:<40} |{flag}"
        )

    print(f"\nTotal Mechanical TPs to Adjudicate: {len(rows)}")
    print("Note: Mechanical matches are not validated semantic discoveries until human root-cause adjudication.")


if __name__ == "__main__":
    generate_adjudication_packet()
