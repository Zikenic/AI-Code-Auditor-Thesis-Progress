import json

with open("data/results/config_b_pilot_run.json", encoding="utf-8") as f:
    b_data = json.load(f)
with open("data/results/config_c_pilot_run.json", encoding="utf-8") as f:
    c_data = json.load(f)

# Collect matches
matches = []

for c in b_data["cases"]:
    cid = c["case_id"]
    for pair in c["evaluation"]["matched_pairs"]:
        # find matching finding
        f_obj = [f for f in c["findings"] if f["finding_id"] == pair["finding_id"]][0]
        matches.append(
            {
                "config": "Config B",
                "case_id": cid,
                "defect_id": pair["defect_id"],
                "matched_cwe": pair["matched_cwe"],
                "method": "direct overlap" if pair["is_direct_overlap"] else "tolerance match (+-10 lines)",
                "finding_id": pair["finding_id"],
                "lines": f"{f_obj['start_line']}-{f_obj['end_line']}",
                "title": f_obj["title"],
                "description": f_obj["description"],
            }
        )

for c in c_data["cases"]:
    cid = c["case_id"]
    for pair in c["evaluation"]["matched_pairs"]:
        f_obj = [f for f in c["findings"] if f["finding_id"] == pair["finding_id"]][0]
        matches.append(
            {
                "config": "Config C",
                "case_id": cid,
                "defect_id": pair["defect_id"],
                "matched_cwe": pair["matched_cwe"],
                "method": "direct overlap" if pair["is_direct_overlap"] else "tolerance match (+-10 lines)",
                "finding_id": pair["finding_id"],
                "lines": f"{f_obj['start_line']}-{f_obj['end_line']}",
                "title": f_obj["title"],
                "description": f_obj["description"],
            }
        )

print(f"Total Matches: {len(matches)}")
for m in matches:
    print(
        f"[{m['config']}] {m['case_id']} | {m['defect_id']} | lines {m['lines']} | {m['method']} | {m['matched_cwe']}"
    )
    print(f"   Title: {m['title']}")
    print(f"   Desc:  {m['description'][:140]}...")
