"""Automated parity verification script for Phase 3B / Phase 3B.1 Configuration A pilot run.

Compares all 17 ground-truth-verified pilot cases between canonical data/pilot_cases.json
and the results artifact data/results/config_a_pilot_run.json across:
1. Target file path
2. Target commit hash
3. Ground-truth defect loci [start_line, end_line]
4. Primary CWE identifier
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

with open(REPO_ROOT / "data" / "pilot_cases.json", encoding="utf-8") as f:
    pilot = json.load(f)

with open(REPO_ROOT / "data" / "results" / "config_a_pilot_run.json", encoding="utf-8") as f:
    results = json.load(f)

pilot_cases = {c["case_id"]: c for c in pilot["cases"] if c.get("verification_status") == "GROUND_TRUTH_VERIFIED"}
result_cases = {c["case_id"]: c for c in results["cases"]}

print(f"Verified pilot cases in canonical dataset: {len(pilot_cases)}")
print(f"Cases in benchmark results: {len(result_cases)}")

discrepancies = []

for cid, pcase in pilot_cases.items():
    rcase = result_cases.get(cid)
    if not rcase:
        discrepancies.append(f"{cid}: Missing from results!")
        continue

    # 1. Compare target file
    p_file = pcase.get("target_file")
    r_file = rcase.get("target_file")
    if p_file != r_file:
        discrepancies.append(f"{cid}: File mismatch: canonical '{p_file}' vs result '{r_file}'")

    # 2. Compare commit hash
    p_commit = pcase.get("commit_hash")
    r_commit = rcase.get("commit_hash")
    if p_commit != r_commit:
        discrepancies.append(f"{cid}: Commit mismatch: canonical '{p_commit}' vs result '{r_commit}'")

    # 3. Compare defect loci
    p_loci = [[d["start_line"], d["end_line"]] for d in pcase.get("defects", [])]
    r_loci = rcase.get("gt_loci", [])
    if p_loci != r_loci:
        discrepancies.append(f"{cid}: Loci mismatch: canonical {p_loci} vs result {r_loci}")

    # 4. Compare primary CWE
    p_cwe = pcase.get("defects", [{}])[0].get("primary_cwe")
    r_cwe = rcase.get("primary_cwe")
    if p_cwe != r_cwe:
        discrepancies.append(f"{cid}: Primary CWE mismatch: canonical '{p_cwe}' vs result '{r_cwe}'")

if not discrepancies:
    print(
        "\nSUCCESS: 100% agreement between data/pilot_cases.json and data/results/config_a_pilot_run.json across all 17 cases!"
    )
    print(f"Cases verified ({len(pilot_cases)}): {', '.join(sorted(pilot_cases.keys()))}")
else:
    print(f"\nFOUND {len(discrepancies)} DISCREPANCIES:")
    for d in discrepancies:
        print("  -", d)
