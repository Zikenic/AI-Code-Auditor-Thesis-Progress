import json

with open("data/results/config_a_18_case_derived_run.json", encoding="utf-8") as f:
    a_data = json.load(f)
with open("data/results/config_c_pilot_run.json", encoding="utf-8") as f:
    c_data = json.load(f)

static_by_case = {c["case_id"]: c["findings"] for c in a_data["cases"]}

print("=== STATIC OVERLAP ANALYSIS (CONFIG C FINDINGS VS INJECTED STATIC FINDINGS) ===")
total_c_findings = 0
total_overlapping = 0

for cc in c_data["cases"]:
    cid = cc["case_id"]
    target_file = cc["target_file"]
    c_findings = cc["findings"]
    s_findings = static_by_case.get(cid, [])

    for cf in c_findings:
        total_c_findings += 1
        # Check overlap: same file and abs line difference <= 10
        overlaps = []
        for sf in s_findings:
            # line distance
            s_min = sf["start_line"]
            s_max = sf["end_line"]
            c_min = cf["start_line"]
            c_max = cf["end_line"]

            # Intersection or +-10 distance
            line_dist = max(0, max(s_min, c_min) - min(s_max, c_max))
            if line_dist <= 10:
                prov = sf.get("provenance") or {}
                r_id = prov.get("rule_code") or prov.get("rule_id") or prov.get("check_id")
                overlaps.append(f"[{sf['tool_name']}:{r_id} at {s_min}-{s_max}]")

        if overlaps:
            total_overlapping += 1
            print(
                f"{cid} {cf['finding_id']} (lines {cf['start_line']}-{cf['end_line']}, {cf['primary_cwe']}): OVERLAPS {', '.join(overlaps)}"
            )

print("-" * 80)
print(f"Total Config C Findings: {total_c_findings}")
print(
    f"Overlapping with injected static findings within +-10 lines: {total_overlapping} ({total_overlapping / total_c_findings * 100:.1f}%)"
)
print(
    f"Non-overlapping (novel LLM findings): {total_c_findings - total_overlapping} ({(total_c_findings - total_overlapping) / total_c_findings * 100:.1f}%)"
)
