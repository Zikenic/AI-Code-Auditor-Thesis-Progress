import json
from collections import defaultdict

with open("data/results/config_a_18_case_derived_run.json", encoding="utf-8") as f:
    a_data = json.load(f)
with open("data/results/config_b_pilot_run.json", encoding="utf-8") as f:
    b_data = json.load(f)
with open("data/results/config_c_pilot_run.json", encoding="utf-8") as f:
    c_data = json.load(f)

ma = a_data["aggregate_metrics"]
mb = b_data["aggregate_metrics"]
mc = c_data["aggregate_metrics"]

print("=== 1. AGGREGATE METRICS COMPARISON ===")
print(
    f"Predictions Emitted:   Config A = {ma['total_predictions']}, Config B = {mb['total_predictions']}, Config C = {mc['total_predictions']}"
)
print(
    f"True Positives (TP):   Config A = {ma['true_positives']}, Config B = {mb['true_positives']}, Config C = {mc['true_positives']}"
)
print(
    f"False Positives (FP):  Config A = {ma['false_positives']}, Config B = {mb['false_positives']}, Config C = {mc['false_positives']}"
)
print(
    f"False Negatives (FN):  Config A = {ma['false_negatives']}, Config B = {mb['false_negatives']}, Config C = {mc['false_negatives']}"
)
print(
    f"Precision:             Config A = {ma['precision'] * 100:.2f}% ({ma['true_positives']}/{ma['total_predictions']}), Config B = {mb['precision'] * 100:.2f}% ({mb['true_positives']}/{mb['total_predictions']}), Config C = {mc['precision'] * 100:.2f}% ({mc['true_positives']}/{mc['total_predictions']})"
)
print(
    f"Recall:                Config A = {ma['recall'] * 100:.2f}% ({ma['true_positives']}/{ma['total_ground_truth_defects']}), Config B = {mb['recall'] * 100:.2f}% ({mb['true_positives']}/{mb['total_ground_truth_defects']}), Config C = {mc['recall'] * 100:.2f}% ({mc['true_positives']}/{mc['total_ground_truth_defects']})"
)
print(
    f"F1 Score:              Config A = {ma['f1_score'] * 100:.2f}%, Config B = {mb['f1_score'] * 100:.2f}%, Config C = {mc['f1_score'] * 100:.2f}%"
)

print("\n=== 2. PER-CASE EVALUATION RESULTS ===")
print("Case ID    | Cat | GT | Conf A (TP/FP/FN) | Conf B (TP/FP/FN) | Conf C (TP/FP/FN) | Config C Status & Matches")
print("-" * 115)
for ca, cb, cc in zip(a_data["cases"], b_data["cases"], c_data["cases"], strict=True):
    cid = ca["case_id"]
    cat = ca["category_id"]
    gt = len(ca["gt_loci"])
    ea = ca["evaluation"]
    eb = cb["evaluation"]
    ec = cc["evaluation"]
    status_c = cc["execution_status"]
    mp_c = [f"{p['defect_id']} ({p['matched_cwe']}, direct={p['is_direct_overlap']})" for p in ec["matched_pairs"]]
    mp_c_str = (
        ", ".join(mp_c) if mp_c else (f"FAILED: {cc.get('failure_reason')[:40]}..." if status_c == "failed" else "None")
    )
    print(
        f"{cid:<10} | {cat:<3} | {gt:<2} | TP={ea['true_positives']} FP={ea['false_positives']} FN={ea['false_negatives']}   | TP={eb['true_positives']} FP={eb['false_positives']} FN={eb['false_negatives']}   | TP={ec['true_positives']} FP={ec['false_positives']} FN={ec['false_negatives']}   | [{status_c}] {mp_c_str}"
    )

print("\n=== 3. PER-CATEGORY RECALL SUMMARY ===")
cat_stats_a = defaultdict(lambda: {"gt": 0, "tp": 0, "fp": 0, "fn": 0})
cat_stats_b = defaultdict(lambda: {"gt": 0, "tp": 0, "fp": 0, "fn": 0})
cat_stats_c = defaultdict(lambda: {"gt": 0, "tp": 0, "fp": 0, "fn": 0})

for ca, cb, cc in zip(a_data["cases"], b_data["cases"], c_data["cases"], strict=True):
    cat = ca["category_id"]
    gt = len(ca["gt_loci"])
    cat_stats_a[cat]["gt"] += gt
    cat_stats_a[cat]["tp"] += ca["evaluation"]["true_positives"]
    cat_stats_a[cat]["fp"] += ca["evaluation"]["false_positives"]
    cat_stats_a[cat]["fn"] += ca["evaluation"]["false_negatives"]

    cat_stats_b[cat]["gt"] += gt
    cat_stats_b[cat]["tp"] += cb["evaluation"]["true_positives"]
    cat_stats_b[cat]["fp"] += cb["evaluation"]["false_positives"]
    cat_stats_b[cat]["fn"] += cb["evaluation"]["false_negatives"]

    cat_stats_c[cat]["gt"] += gt
    cat_stats_c[cat]["tp"] += cc["evaluation"]["true_positives"]
    cat_stats_c[cat]["fp"] += cc["evaluation"]["false_positives"]
    cat_stats_c[cat]["fn"] += cc["evaluation"]["false_negatives"]

for cat in sorted(cat_stats_a.keys()):
    sa = cat_stats_a[cat]
    sb = cat_stats_b[cat]
    sc = cat_stats_c[cat]
    ra = (sa["tp"] / sa["gt"]) * 100 if sa["gt"] else 0
    rb = (sb["tp"] / sb["gt"]) * 100 if sb["gt"] else 0
    rc = (sc["tp"] / sc["gt"]) * 100 if sc["gt"] else 0
    print(f"Category {cat} (GT={sa['gt']}):")
    print(f"  Config A: TP={sa['tp']}/{sa['gt']} ({ra:.1f}%), FP={sa['fp']}")
    print(f"  Config B: TP={sb['tp']}/{sb['gt']} ({rb:.1f}%), FP={sb['fp']}")
    print(f"  Config C: TP={sc['tp']}/{sc['gt']} ({rc:.1f}%), FP={sc['fp']}")
