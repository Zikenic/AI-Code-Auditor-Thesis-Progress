#!/usr/bin/env python3
"""Deterministic forensic reconciliation and reconstruction of Configurations A, B, C, and D.

Adheres strictly to Phase 5D:
- Purely offline: zero network, model, gateway, or tokenizer calls.
- Preserves all frozen result artifacts without modification.
- Independently recomputes all matches and metrics from raw frozen predictions using
  the unchanged OfflineEvaluationMatcher(tolerance_lines=10).
- Produces an auditable JSON report to data/results/abcd_reconciliation_audit.json.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from auditor.dataset.pilot_loader import load_pilot_cases_from_json
from auditor.matcher.engine import OfflineEvaluationMatcher
from auditor.models.finding import PredictedFinding
from auditor.models.ground_truth import BenchmarkCase

REPO_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILES = {
    "pilot": REPO_ROOT / "data" / "pilot_cases.json",
    "config_a_pilot": REPO_ROOT / "data" / "results" / "config_a_pilot_run.json",
    "config_a_derived": REPO_ROOT / "data" / "results" / "config_a_18_case_derived_run.json",
    "config_b": REPO_ROOT / "data" / "results" / "config_b_pilot_run.json",
    "config_c": REPO_ROOT / "data" / "results" / "config_c_pilot_run.json",
    "config_d": REPO_ROOT / "data" / "results" / "config_d_pilot_run.json",
}

OUTPUT_AUDIT_JSON = REPO_ROOT / "data" / "results" / "abcd_reconciliation_audit.json"


def sha256_file(path: Path) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def compute_metrics(tp: int, fp: int, fn: int) -> dict[str, float]:
    p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
    return {
        "precision": round(p, 6),
        "recall": round(r, 6),
        "f1": round(f1, 6),
        "precision_pct": round(p * 100, 2),
        "recall_pct": round(r * 100, 2),
        "f1_pct": round(f1 * 100, 2),
    }


def run_reconciliation() -> dict[str, Any]:
    # 1. Compute input hashes
    input_hashes = {name: sha256_file(path) for name, path in INPUT_FILES.items()}

    # 2. Load benchmark cases
    pilot_cases: list[BenchmarkCase] = load_pilot_cases_from_json(only_verified=True)

    # 3. Load result artifacts
    results_raw: dict[str, dict] = {}
    for name in ["config_a_derived", "config_b", "config_c", "config_d"]:
        with open(INPUT_FILES[name], encoding="utf-8") as f:
            results_raw[name] = json.load(f)

    matcher = OfflineEvaluationMatcher(tolerance_lines=10)

    per_case_rows: list[dict[str, Any]] = []
    cfgs = [
        ("Config A", "config_a_derived"),
        ("Config B", "config_b"),
        ("Config C", "config_c"),
        ("Config D", "config_d"),
    ]

    for bcase in pilot_cases:
        cid = bcase.case_id
        gt_defects = bcase.defects
        gt_loci_info = [
            {
                "defect_id": d.defect_id,
                "file_path": d.file_path,
                "start_line": d.start_line,
                "end_line": d.end_line,
                "primary_cwe": d.primary_cwe,
            }
            for d in gt_defects
        ]

        row: dict[str, Any] = {
            "case_id": cid,
            "category_id": bcase.category_id if hasattr(bcase, "category_id") else gt_defects[0].category_id,
            "gt_defect_count": len(gt_defects),
            "gt_loci": gt_loci_info,
            "configurations": {},
        }

        for cfg_label, artifact_key in cfgs:
            raw_artifact = results_raw[artifact_key]
            case_data = next((c for c in raw_artifact.get("cases", []) if c["case_id"] == cid), None)

            if not case_data:
                row["configurations"][cfg_label] = {
                    "status": "missing",
                    "predictions_count": 0,
                    "tp": 0,
                    "fp": 0,
                    "fn": len(gt_defects),
                    "matched_pairs": [],
                    "recomputed_tp": 0,
                    "recomputed_fp": 0,
                    "recomputed_fn": len(gt_defects),
                    "recomputed_matched_pairs": [],
                    "match_parity": True,
                }
                continue

            status = case_data.get("execution_status", "success")
            failure_reason = case_data.get("failure_reason")

            # Under FR-09: failed cases have predictions discarded from primary scoring
            if status == "failed":
                row["configurations"][cfg_label] = {
                    "status": "failed",
                    "failure_reason": failure_reason,
                    "predictions_count": 0,
                    "tp": 0,
                    "fp": 0,
                    "fn": len(gt_defects),
                    "matched_pairs": [],
                    "recomputed_tp": 0,
                    "recomputed_fp": 0,
                    "recomputed_fn": len(gt_defects),
                    "recomputed_matched_pairs": [],
                    "match_parity": True,
                }
            else:
                stored_eval = case_data.get("evaluation", {})
                stored_tp = stored_eval.get("true_positives", 0)
                stored_fp = stored_eval.get("false_positives", 0)
                stored_fn = stored_eval.get("false_negatives", 0)
                stored_mp = stored_eval.get("matched_pairs", [])

                raw_findings = case_data.get("findings", [])
                pred_objs = [PredictedFinding(**f) for f in raw_findings]
                recomputed_res = matcher.evaluate_case(bcase, pred_objs)

                recomputed_tp = recomputed_res.true_positives
                recomputed_fp = recomputed_res.false_positives
                recomputed_fn = recomputed_res.false_negatives
                recomputed_mp = [m.model_dump() for m in recomputed_res.matched_pairs]

                parity = (
                    stored_tp == recomputed_tp
                    and stored_fp == recomputed_fp
                    and stored_fn == recomputed_fn
                    and len(stored_mp) == len(recomputed_mp)
                )

                row["configurations"][cfg_label] = {
                    "status": "success",
                    "failure_reason": None,
                    "predictions_count": len(raw_findings),
                    "tp": stored_tp,
                    "fp": stored_fp,
                    "fn": stored_fn,
                    "matched_pairs": stored_mp,
                    "recomputed_tp": recomputed_tp,
                    "recomputed_fp": recomputed_fp,
                    "recomputed_fn": recomputed_fn,
                    "recomputed_matched_pairs": recomputed_mp,
                    "match_parity": parity,
                }

        per_case_rows.append(row)

    # 4. Compute primary aggregate metrics
    aggregates: dict[str, Any] = {}
    for cfg_label, _ in cfgs:
        tot_cases = len(per_case_rows)
        completed_cases = sum(1 for r in per_case_rows if r["configurations"][cfg_label]["status"] == "success")
        failed_cases = tot_cases - completed_cases
        gt_denom = sum(r["gt_defect_count"] for r in per_case_rows)
        preds_tot = sum(r["configurations"][cfg_label]["predictions_count"] for r in per_case_rows)
        tp_tot = sum(r["configurations"][cfg_label]["tp"] for r in per_case_rows)
        fp_tot = sum(r["configurations"][cfg_label]["fp"] for r in per_case_rows)
        fn_tot = sum(r["configurations"][cfg_label]["fn"] for r in per_case_rows)

        metrics = compute_metrics(tp_tot, fp_tot, fn_tot)

        aggregates[cfg_label] = {
            "total_cases": tot_cases,
            "completed_cases": completed_cases,
            "failed_cases": failed_cases,
            "gt_denominator": gt_denom,
            "predictions_count": preds_tot,
            "tp": tp_tot,
            "fp": fp_tot,
            "fn": fn_tot,
            **metrics,
        }

    # 5. Compute paired subset: Config B vs Config C on 17 matched cases (exclude CAND-0008)
    paired_17_cases = [r["case_id"] for r in per_case_rows if r["case_id"] != "CAND-0008"]
    paired_17_rows = [r for r in per_case_rows if r["case_id"] != "CAND-0008"]
    paired_17_results: dict[str, Any] = {"included_case_ids": paired_17_cases}

    for cfg_label in ["Config B", "Config C"]:
        gt_denom = sum(r["gt_defect_count"] for r in paired_17_rows)
        preds_tot = sum(r["configurations"][cfg_label]["predictions_count"] for r in paired_17_rows)
        tp_tot = sum(r["configurations"][cfg_label]["tp"] for r in paired_17_rows)
        fp_tot = sum(r["configurations"][cfg_label]["fp"] for r in paired_17_rows)
        fn_tot = sum(r["configurations"][cfg_label]["fn"] for r in paired_17_rows)
        metrics = compute_metrics(tp_tot, fp_tot, fn_tot)

        per_case_fps = {r["case_id"]: r["configurations"][cfg_label]["fp"] for r in paired_17_rows}

        paired_17_results[cfg_label] = {
            "gt_denominator": gt_denom,
            "predictions_count": preds_tot,
            "tp": tp_tot,
            "fp": fp_tot,
            "fn": fn_tot,
            **metrics,
            "per_case_fp": per_case_fps,
        }

    # Config B's CAND-0008 per-case breakdown
    cand_0008_row = next(r for r in per_case_rows if r["case_id"] == "CAND-0008")
    cand_0008_b_fp = cand_0008_row["configurations"]["Config B"]["fp"]
    paired_17_results["config_b_cand_0008_fp"] = cand_0008_b_fp
    paired_17_results["config_b_reconciliation_math"] = (
        f"18-case FP ({aggregates['Config B']['fp']}) - CAND-0008 FP ({cand_0008_b_fp}) = {aggregates['Config B']['fp'] - cand_0008_b_fp}"
    )

    # 6. Common completed subset across B, C, and D
    common_cases = [
        r["case_id"]
        for r in per_case_rows
        if r["configurations"]["Config B"]["status"] == "success"
        and r["configurations"]["Config C"]["status"] == "success"
        and r["configurations"]["Config D"]["status"] == "success"
    ]
    common_rows = [r for r in per_case_rows if r["case_id"] in common_cases]
    common_results: dict[str, Any] = {
        "included_case_ids": common_cases,
        "excluded_cases": {
            r["case_id"]: {
                "Config B": r["configurations"]["Config B"]["status"],
                "Config C": r["configurations"]["Config C"]["status"],
                "Config D": r["configurations"]["Config D"]["status"],
            }
            for r in per_case_rows
            if r["case_id"] not in common_cases
        },
    }

    for cfg_label in ["Config B", "Config C", "Config D"]:
        gt_denom = sum(r["gt_defect_count"] for r in common_rows)
        preds_tot = sum(r["configurations"][cfg_label]["predictions_count"] for r in common_rows)
        tp_tot = sum(r["configurations"][cfg_label]["tp"] for r in common_rows)
        fp_tot = sum(r["configurations"][cfg_label]["fp"] for r in common_rows)
        fn_tot = sum(r["configurations"][cfg_label]["fn"] for r in common_rows)
        metrics = compute_metrics(tp_tot, fp_tot, fn_tot)

        per_case_fps = {r["case_id"]: r["configurations"][cfg_label]["fp"] for r in common_rows}

        common_results[cfg_label] = {
            "gt_denominator": gt_denom,
            "predictions_count": preds_tot,
            "tp": tp_tot,
            "fp": fp_tot,
            "fn": fn_tot,
            **metrics,
            "per_case_fp": per_case_fps,
        }

    # 7. Category metrics reconciliation
    cat_results: dict[int, dict[str, Any]] = {}
    for cat_id in range(1, 7):
        cat_rows = [r for r in per_case_rows if r["category_id"] == cat_id]
        cat_gt = sum(r["gt_defect_count"] for r in cat_rows)
        cat_results[cat_id] = {
            "category_id": cat_id,
            "cases_count": len(cat_rows),
            "gt_defects": cat_gt,
            "configurations": {},
        }
        for cfg_label, _ in cfgs:
            c_tp = sum(r["configurations"][cfg_label]["tp"] for r in cat_rows)
            c_fn = sum(r["configurations"][cfg_label]["fn"] for r in cat_rows)
            c_fp_by_case = sum(r["configurations"][cfg_label]["fp"] for r in cat_rows)
            c_rec = round(c_tp / cat_gt * 100, 2) if cat_gt > 0 else 0.0
            cat_results[cat_id]["configurations"][cfg_label] = {
                "tp": c_tp,
                "fn": c_fn,
                "recall_pct": c_rec,
                "fp_by_case_category": c_fp_by_case,
            }

    audit_data = {
        "metadata": {
            "tool": "tools/print_abcd_rows.py",
            "offline_only": True,
            "matcher": "OfflineEvaluationMatcher(tolerance_lines=10)",
            "input_hashes": input_hashes,
        },
        "per_case_audit": per_case_rows,
        "primary_aggregates": aggregates,
        "paired_17_cases": paired_17_results,
        "common_completed_subset": common_results,
        "per_category_reconciliation": cat_results,
    }

    # Save to disk
    with open(OUTPUT_AUDIT_JSON, "w", encoding="utf-8") as f:
        json.dump(audit_data, f, indent=2)

    return audit_data


def print_audit_report(audit_data: dict[str, Any]) -> None:
    print("=" * 110)
    print("PHASE 5D FORENSIC RECONCILIATION: PER-CASE AUDIT TABLE (CONFIGURATIONS A, B, C, D)")
    print("=" * 110)
    header = (
        f"{'Case ID':<10} | {'Cat':<3} | {'GT':<2} | "
        f"{'Cfg A (TP/FP/FN)':<17} | "
        f"{'Cfg B (TP/FP/FN)':<17} | "
        f"{'Cfg C (TP/FP/FN)':<17} | "
        f"{'Cfg D (TP/FP/FN)':<17}"
    )
    print(header)
    print("-" * 110)

    for r in audit_data["per_case_audit"]:
        cid = r["case_id"]
        cat = r["category_id"]
        gt = r["gt_defect_count"]

        cols = []
        for cfg in ["Config A", "Config B", "Config C", "Config D"]:
            info = r["configurations"][cfg]
            if info["status"] == "failed":
                cols.append(f"FAIL ({info['tp']}/{info['fp']}/{info['fn']})")
            else:
                cols.append(f"OK   ({info['tp']}/{info['fp']}/{info['fn']})")

        print(f"{cid:<10} | {cat:<3} | {gt:<2} | {cols[0]:<17} | {cols[1]:<17} | {cols[2]:<17} | {cols[3]:<17}")

    print("-" * 110)
    print("\nPRIMARY AGGREGATE SUMMARY:")
    for cfg in ["Config A", "Config B", "Config C", "Config D"]:
        agg = audit_data["primary_aggregates"][cfg]
        print(
            f"  {cfg:<10}: Cases={agg['completed_cases']}/{agg['total_cases']} | "
            f"GT={agg['gt_denominator']} | Preds={agg['predictions_count']} | "
            f"TP={agg['tp']} | FP={agg['fp']} | FN={agg['fn']} | "
            f"P={agg['precision_pct']:.2f}% | R={agg['recall_pct']:.2f}% | F1={agg['f1_pct']:.2f}%"
        )

    print("\nPAIRED 17-CASE COMPARISON (CONFIG B vs CONFIG C, EXCLUDING CAND-0008):")
    p17 = audit_data["paired_17_cases"]
    print(f"  Included cases ({len(p17['included_case_ids'])}): {', '.join(p17['included_case_ids'])}")
    print(
        f"  Config B: TP={p17['Config B']['tp']}, FP={p17['Config B']['fp']}, FN={p17['Config B']['fn']}, P={p17['Config B']['precision_pct']}%, R={p17['Config B']['recall_pct']}%, F1={p17['Config B']['f1_pct']}%"
    )
    print(
        f"  Config C: TP={p17['Config C']['tp']}, FP={p17['Config C']['fp']}, FN={p17['Config C']['fn']}, P={p17['Config C']['precision_pct']}%, R={p17['Config C']['recall_pct']}%, F1={p17['Config C']['f1_pct']}%"
    )
    print(f"  Reconciliation: {p17['config_b_reconciliation_math']}")

    print("\nCOMMON COMPLETED SUBSET ACROSS B, C, D:")
    ccs = audit_data["common_completed_subset"]
    print(f"  Included cases ({len(ccs['included_case_ids'])}): {', '.join(ccs['included_case_ids'])}")
    print(f"  Excluded cases: {ccs['excluded_cases']}")
    for cfg in ["Config B", "Config C", "Config D"]:
        info = ccs[cfg]
        print(
            f"  {cfg:<10}: GT={info['gt_denominator']} | TP={info['tp']} | FP={info['fp']} | FN={info['fn']} | P={info['precision_pct']}% | R={info['recall_pct']}% | F1={info['f1_pct']}%"
        )

    print("\nPER-CATEGORY RECONCILIATION:")
    print(
        f"{'Cat':<4} | {'GT':<3} | {'Cfg A (TP/FP/R)':<17} | {'Cfg B (TP/FP/R)':<17} | {'Cfg C (TP/FP/R)':<17} | {'Cfg D (TP/FP/R)':<17}"
    )
    print("-" * 85)
    for cat_id in range(1, 7):
        cat = audit_data["per_category_reconciliation"][cat_id]
        gt = cat["gt_defects"]
        cols = []
        for cfg in ["Config A", "Config B", "Config C", "Config D"]:
            info = cat["configurations"][cfg]
            cols.append(f"{info['tp']}/{info['fp_by_case_category']}/{info['recall_pct']}%")
        print(f"Cat {cat_id:<1} | {gt:<3} | {cols[0]:<17} | {cols[1]:<17} | {cols[2]:<17} | {cols[3]:<17}")

    print("=" * 110)


if __name__ == "__main__":
    data = run_reconciliation()
    print_audit_report(data)
