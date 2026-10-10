"""Deterministic census computation script for AI Code Auditor benchmark.

Reads:
- Canonical dataset: data/pilot_cases.json
- Candidate staging queue: Project Documents/dataset/candidate_queue.md

Computes exact case, defect, locus, file, and lifecycle statistics.
"""

import json
import re
from pathlib import Path
from typing import Any


def compute_census(
    canonical_json_path: Path | str = "data/pilot_cases.json",
    queue_md_path: Path | str = "Project Documents/dataset/candidate_queue.md",
) -> dict[str, Any]:
    canonical_path = Path(canonical_json_path)
    queue_path = Path(queue_md_path)

    # 1. Canonical dataset census
    with open(canonical_path, encoding="utf-8") as f:
        canonical_data = json.load(f)

    cases = canonical_data.get("cases", [])
    canonical_case_count = len(cases)

    verification_status_counts: dict[str, int] = {}
    reproducer_status_counts: dict[str, int] = {}
    total_defects = 0
    gt_defects = 0
    sv_defects = 0
    target_files_list: list[str] = []
    contextual_files_set: set[str] = set()
    loci_list: list[tuple[str, int, int]] = []

    for c in cases:
        v_stat = c.get("verification_status", "GROUND_TRUTH_VERIFIED")
        verification_status_counts[v_stat] = verification_status_counts.get(v_stat, 0) + 1

        r_stat = c.get("reproducer_status", "not_attempted")
        reproducer_status_counts[r_stat] = reproducer_status_counts.get(r_stat, 0) + 1

        case_defects = c.get("defects", [])
        total_defects += len(case_defects)
        if v_stat == "GROUND_TRUTH_VERIFIED":
            gt_defects += len(case_defects)
        elif v_stat == "SOURCE_VERIFIED":
            sv_defects += len(case_defects)

        t_file = c.get("target_file")
        if t_file:
            target_files_list.append(t_file)
        else:
            for df in case_defects:
                target_files_list.append(df["file_path"])

        for ctx in c.get("contextual_files", []):
            contextual_files_set.add(ctx)

        for df in case_defects:
            loci_list.append((df["file_path"], df["start_line"], df["end_line"]))

    distinct_target_files = sorted(set(target_files_list))
    distinct_loci = sorted(set(loci_list))
    file_union = sorted(set(target_files_list) | contextual_files_set)

    # 2. Candidate queue census
    with open(queue_path, encoding="utf-8") as f:
        queue_text = f.read()

    pattern = r"###\s+(CAND-\d{4}):\s*([^\n]+)(.*?)(?=(?:###\s+CAND-\d{4}:|##\s+\d+\.|\Z))"
    cand_matches = re.findall(pattern, queue_text, re.DOTALL)

    queue_lifecycle_counts: dict[str, int] = {}
    queue_candidates_by_status: dict[str, list[str]] = {}

    for cid, _title, body in cand_matches:
        v_m = re.search(r"-\s*\*\*Verification Status\*\*:\s*`?([A-Za-z0-9_]+)`?", body)
        v_stat = v_m.group(1) if v_m else "UNKNOWN"
        queue_lifecycle_counts[v_stat] = queue_lifecycle_counts.get(v_stat, 0) + 1
        queue_candidates_by_status.setdefault(v_stat, []).append(cid)

    rej_pattern = r"(REJ-\d{4})"
    rejected_leads = sorted(set(re.findall(rej_pattern, queue_text)))

    return {
        "canonical": {
            "case_count": canonical_case_count,
            "verification_status_counts": verification_status_counts,
            "reproducer_status_counts": reproducer_status_counts,
            "total_defects": total_defects,
            "gt_verified_defects": gt_defects,
            "source_verified_defects": sv_defects,
            "distinct_loci_count": len(distinct_loci),
            "distinct_target_files_count": len(distinct_target_files),
            "distinct_target_files": distinct_target_files,
            "distinct_contextual_files_count": len(contextual_files_set),
            "distinct_contextual_files": sorted(contextual_files_set),
            "file_union_count": len(file_union),
        },
        "queue": {
            "total_staged_candidates": len(cand_matches),
            "lifecycle_counts": queue_lifecycle_counts,
            "candidates_by_status": queue_candidates_by_status,
            "rejected_leads_count": len(rejected_leads),
            "rejected_leads": rejected_leads,
            "accepted_into_benchmark": 0,
        },
    }


def main() -> None:
    census = compute_census()
    can = census["canonical"]
    q = census["queue"]

    print("=" * 60)
    print("AI CODE AUDITOR DETERMINISTIC BENCHMARK CENSUS")
    print("=" * 60)
    print("\n1. Canonical Dataset (data/pilot_cases.json):")
    print(f"   Canonical Cases:                 {can['case_count']}")
    print(f"   - GROUND_TRUTH_VERIFIED:        {can['verification_status_counts'].get('GROUND_TRUTH_VERIFIED', 0)}")
    print(f"   - SOURCE_VERIFIED (Pending):    {can['verification_status_counts'].get('SOURCE_VERIFIED', 0)}")
    print("\n   Reproducer Status Breakdown:")
    for r_stat, cnt in sorted(can["reproducer_status_counts"].items()):
        print(f"   - {r_stat:30s}: {cnt}")
    print(f"\n   Defect Records:                  {can['total_defects']}")
    print(f"   - In GT Verified Cases:         {can['gt_verified_defects']}")
    print(f"   - In Source Verified Cases:     {can['source_verified_defects']}")
    print(f"   Distinct Defect Loci (ranges):   {can['distinct_loci_count']}")
    print(f"   Distinct Target Files:           {can['distinct_target_files_count']}")
    print(
        f"   Distinct Contextual Files:       {can['distinct_contextual_files_count']} ({can['distinct_contextual_files']})"
    )
    print(f"   Target + Contextual File Union:  {can['file_union_count']}")

    print("\n2. Staging Queue (candidate_queue.md):")
    print(f"   Total Staged Candidates:         {q['total_staged_candidates']}")
    for st, cnt in sorted(q["lifecycle_counts"].items()):
        print(f"   - {st:30s}: {cnt}")
    print(f"   Rejected Leads Register:         {q['rejected_leads_count']} ({q['rejected_leads']})")
    print(f"   Accepted Into Final Benchmark:   {q['accepted_into_benchmark']} / 100")
    print("=" * 60)


if __name__ == "__main__":
    main()
