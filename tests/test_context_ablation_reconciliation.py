"""Regression tests for context ablation finding ledger reconciliation and one-to-one accounting."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_RESULTS_PATH = REPO_ROOT / "data" / "results" / "context_ablation_pilot" / "pilot_run" / "ablation_results.json"
LEDGER_JSON_PATH = REPO_ROOT / "data" / "ablation_canonical_ledger.json"
LEDGER_CSV_PATH = REPO_ROOT / "data" / "results" / "context_ablation_pilot" / "canonical_finding_ledger.csv"
SUMMARY_JSON_PATH = REPO_ROOT / "data" / "results" / "context_ablation_pilot" / "ledger_metrics_summary.json"
BENCHMARK_JSON_PATH = REPO_ROOT / "data" / "results" / "context_ablation_pilot" / "pbkdf2_benchmark_measurements.json"
REPORT_MD_PATH = REPO_ROOT / "Project Documents" / "reports" / "context_ablation_reconciliation_report.md"


def test_raw_to_ledger_one_to_one_accounting():
    """Verify every raw finding maps to exactly one ledger row with no omissions or fabrications."""
    with open(RAW_RESULTS_PATH, encoding="utf-8") as f:
        raw_data = json.load(f)
    with open(LEDGER_JSON_PATH, encoding="utf-8") as f:
        ledger_data = json.load(f)
    with open(LEDGER_CSV_PATH, encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))

    # 1. Total findings count
    raw_findings_count = sum(len(c["findings"]) for c in raw_data["results"])
    assert raw_findings_count == 27
    assert len(ledger_data) == 27
    assert len(csv_rows) == 27

    # 2. Check stable identity mapping
    ledger_ids = [entry["finding_id"] for entry in ledger_data]
    csv_ids = [row["finding_id"] for row in csv_rows]
    assert len(set(ledger_ids)) == 27, "Duplicate finding_id found in ledger"
    assert ledger_ids == csv_ids, "Ledger JSON and CSV finding IDs do not match"

    # 3. Check every raw item is matched by (slot, finding_index)
    for entry in ledger_data:
        slot_idx = entry["raw_slot_index"]
        f_idx = entry["raw_finding_index"]
        raw_case = raw_data["results"][slot_idx]
        raw_finding = raw_case["findings"][f_idx]
        assert entry["fixture_id"] == raw_case["fixture_id"]
        assert entry["arm"] == f"Arm {raw_case['arm']}"
        assert entry["raw_title"] == raw_finding.get("title")
        assert entry["raw_description"] == raw_finding.get("description")


def test_category_and_arm_totals():
    """Verify category totals sum exactly to raw finding totals in each arm."""
    with open(LEDGER_JSON_PATH, encoding="utf-8") as f:
        ledger = json.load(f)

    arm_n = [e for e in ledger if e["arm"] == "Arm N"]
    arm_r = [e for e in ledger if e["arm"] == "Arm R"]

    assert len(arm_n) == 14
    assert len(arm_r) == 13

    # Primary category breakdown for Arm N
    n_vulns = sum(1 for e in arm_n if e["primary_category"] == "1_confirmed_security_vulnerability")
    n_defects = sum(1 for e in arm_n if e["primary_category"] == "2_confirmed_correctness_or_reliability_defect")
    n_concerns = sum(1 for e in arm_n if e["primary_category"] == "3_plausible_or_unresolved_concern")
    n_fps = sum(1 for e in arm_n if e["primary_category"] == "4_supported_false_positive")
    n_dupes = sum(1 for e in arm_n if e["primary_category"] == "5_duplicate_finding")
    n_unadj = sum(1 for e in arm_n if e["primary_category"] == "6_not_adjudicable")

    assert n_vulns == 0
    assert n_defects == 2  # ABL-0006-N-2 (decode crash), ABL-0006-N-3 (key rotation drop)
    assert n_concerns == 2  # ABL-0002-N-1 (unused user id), ABL-0004-N-3 (password length DoS)
    assert n_fps == 10
    assert n_dupes == 0
    assert n_unadj == 0
    assert (n_vulns + n_defects + n_concerns + n_fps + n_dupes + n_unadj) == 14

    # Primary category breakdown for Arm R
    r_vulns = sum(1 for e in arm_r if e["primary_category"] == "1_confirmed_security_vulnerability")
    r_defects = sum(1 for e in arm_r if e["primary_category"] == "2_confirmed_correctness_or_reliability_defect")
    r_concerns = sum(1 for e in arm_r if e["primary_category"] == "3_plausible_or_unresolved_concern")
    r_fps = sum(1 for e in arm_r if e["primary_category"] == "4_supported_false_positive")
    r_dupes = sum(1 for e in arm_r if e["primary_category"] == "5_duplicate_finding")
    r_unadj = sum(1 for e in arm_r if e["primary_category"] == "6_not_adjudicable")

    assert r_vulns == 0
    assert r_defects == 2  # ABL-0006-R-2 (key rotation drop), ABL-0006-R-3 (decode crash)
    assert r_concerns == 4  # ABL-0001-R-3 (TOCTOU), ABL-0002-R-2 (unused user id), ABL-0004-R-2 (100k iter), ABL-0005-R-1 (unhandled stream cap)
    assert r_fps == 7
    assert r_dupes == 0
    assert r_unadj == 0
    assert (r_vulns + r_defects + r_concerns + r_fps + r_dupes + r_unadj) == 13


def test_multi_tier_clean_cohort_reconciliation():
    """Verify multi-tier denominator evaluation: D=5 (operational), D=4 (comprehensive security), and D=1 (zero code smell)."""
    with open(SUMMARY_JSON_PATH, encoding="utf-8") as f:
        summary = json.load(f)

    # 1. Tier 1: Operational Online-Authentication Cohort (D=5)
    d5 = summary["operational_clean_cohort_d5"]
    assert d5["denominator"] == 5
    assert d5["eligible_fixtures"] == ["ABL-0001", "ABL-0002", "ABL-0003", "ABL-0004", "ABL-0005"]
    assert d5["arm_n"]["total_candidate_findings"] == 10
    assert d5["arm_n"]["supported_false_positives"] == 8
    assert d5["arm_r"]["total_candidate_findings"] == 9
    assert d5["arm_r"]["supported_false_positives"] == 5
    assert d5["delta_r_minus_n"]["false_positives"] == -3
    assert d5["delta_r_minus_n"]["total_findings"] == -1

    # 2. Tier 2: Comprehensive Security-Clean Cohort (D=4, excluding ABL-0006 and ABL-0004)
    d4 = summary["comprehensive_security_clean_cohort_d4"]
    assert d4["denominator"] == 4
    assert d4["eligible_fixtures"] == ["ABL-0001", "ABL-0002", "ABL-0003", "ABL-0005"]
    assert d4["arm_n"]["total_candidate_findings"] == 7
    assert d4["arm_n"]["supported_false_positives"] == 6
    assert d4["arm_r"]["total_candidate_findings"] == 6
    assert d4["arm_r"]["supported_false_positives"] == 3
    assert d4["delta_r_minus_n"]["false_positives"] == -3
    assert d4["delta_r_minus_n"]["total_findings"] == -1

    # Backwards compatibility check
    assert summary["strict_clean_cohort_d4"] == d4

    # 3. Tier 3: Lint-Clean / Zero-Code-Smell Cohort (D=1, ABL-0003 only)
    d1 = summary["zero_code_smell_cohort_d1"]
    assert d1["denominator"] == 1
    assert d1["eligible_fixtures"] == ["ABL-0003"]
    assert d1["arm_n"]["total_candidate_findings"] == 2
    assert d1["arm_n"]["supported_false_positives"] == 2
    assert d1["arm_r"]["total_candidate_findings"] == 0
    assert d1["arm_r"]["supported_false_positives"] == 0
    assert d1["delta_r_minus_n"]["false_positives"] == -2
    assert d1["delta_r_minus_n"]["total_findings"] == -2


def test_abl_0006_and_abl_0004_exclusions():
    """Verify exact excluded finding IDs and arithmetic for excluded fixtures."""
    with open(SUMMARY_JSON_PATH, encoding="utf-8") as f:
        summary = json.load(f)

    # ABL-0006 excluded findings (4 in N, 4 in R)
    excl_0006 = summary["excluded_cohort_abl0006"]
    assert excl_0006["excluded_finding_ids"]["arm_n"] == [
        "ABL-0006-N-1",
        "ABL-0006-N-2",
        "ABL-0006-N-3",
        "ABL-0006-N-4",
    ]
    assert excl_0006["excluded_finding_ids"]["arm_r"] == [
        "ABL-0006-R-1",
        "ABL-0006-R-2",
        "ABL-0006-R-3",
        "ABL-0006-R-4",
    ]
    assert excl_0006["arm_n"]["confirmed_correctness_reliability_defects"] == 2
    assert excl_0006["arm_n"]["supported_false_positives"] == 2
    assert excl_0006["arm_r"]["confirmed_correctness_reliability_defects"] == 2
    assert excl_0006["arm_r"]["supported_false_positives"] == 2

    # ABL-0004 excluded findings (3 in N, 3 in R)
    excl_0004 = summary["excluded_cohort_abl0004"]
    assert excl_0004["excluded_finding_ids"]["arm_n"] == [
        "ABL-0004-N-1",
        "ABL-0004-N-2",
        "ABL-0004-N-3",
    ]
    assert excl_0004["excluded_finding_ids"]["arm_r"] == [
        "ABL-0004-R-1",
        "ABL-0004-R-2",
        "ABL-0004-R-3",
    ]
    assert excl_0004["arm_n"]["supported_false_positives"] == 2
    assert excl_0004["arm_n"]["plausible_or_unresolved_concerns"] == 1
    assert excl_0004["arm_r"]["supported_false_positives"] == 2
    assert excl_0004["arm_r"]["plausible_or_unresolved_concerns"] == 1

    # Arithmetic consequence: since ABL-0004 had exactly 2 FPs in both arms, delta between arms on ABL-0004 is 0.
    # Therefore, subtracting ABL-0004 leaves the false positive delta unchanged between D=5 (-3) and D=4 (-3).
    delta_abl0004_fps = excl_0004["arm_r"]["supported_false_positives"] - excl_0004["arm_n"]["supported_false_positives"]
    assert delta_abl0004_fps == 0


def test_per_fixture_sums_match_arm_aggregates():
    """Verify that per-fixture counts sum up to the arm totals."""
    with open(SUMMARY_JSON_PATH, encoding="utf-8") as f:
        summary = json.load(f)

    per_fx = summary["per_fixture_breakdown"]
    arm_n_total = sum(per_fx[f]["arm_n"]["total"] for f in per_fx)
    arm_r_total = sum(per_fx[f]["arm_r"]["total"] for f in per_fx)
    arm_n_fps = sum(per_fx[f]["arm_n"]["false_positives"] for f in per_fx)
    arm_r_fps = sum(per_fx[f]["arm_r"]["false_positives"] for f in per_fx)

    assert arm_n_total == 14
    assert arm_r_total == 13
    assert arm_n_fps == 10
    assert arm_r_fps == 7


def test_methodological_interpretation_and_overlap_labeling():
    """Verify that summary explicitly qualifies tiers as overlapping sensitivity subsets."""
    with open(SUMMARY_JSON_PATH, encoding="utf-8") as f:
        summary = json.load(f)

    interp = summary.get("methodological_interpretation", "")
    assert "overlapping" in interp.lower()
    assert "post-hoc" in interp.lower()
    assert "not constitute independent replications" in interp.lower()


def test_v2_exclusion_from_canonical_v1_ledger():
    """Verify that all ledger entries represent strictly original v1 pilot records."""
    with open(LEDGER_JSON_PATH, encoding="utf-8") as f:
        ledger = json.load(f)

    for entry in ledger:
        assert entry["fixture_version"] == "v1"
        assert "_v2" not in entry["fixture_id"]


def test_benchmark_provenance_and_measurements():
    """Verify benchmark provenance file exists with valid 10-repetition statistical measurements."""
    assert BENCHMARK_JSON_PATH.exists()
    with open(BENCHMARK_JSON_PATH, encoding="utf-8") as f:
        bench_data = json.load(f)

    assert bench_data["benchmark_metadata"]["num_repetitions"] == 10
    measurements = bench_data["measurements"]
    assert len(measurements) == 4

    for m in measurements:
        raw = m["raw_timings_ms"]
        assert len(raw) == 10
        # Check mean formula
        calc_mean = round(sum(raw) / len(raw), 2)
        assert abs(calc_mean - m["mean_ms"]) <= 0.02
        # Check sample standard deviation formula
        variance = sum((x - (sum(raw) / len(raw))) ** 2 for x in raw) / 9
        calc_stdev = round(math.sqrt(variance), 2)
        assert abs(calc_stdev - m["stdev_ms"]) <= 0.02


def test_markdown_report_matches_ledger_metrics():
    """Verify Markdown report text aligns exactly with canonical summary metrics."""
    assert REPORT_MD_PATH.exists()
    report_text = REPORT_MD_PATH.read_text(encoding="utf-8")

    # Verify key counts appear in the report
    assert "**14**" in report_text  # Arm N total
    assert "**13**" in report_text  # Arm R total
    assert "**10**" in report_text  # Arm N FPs total
    assert "**7**" in report_text   # Arm R FPs total
    assert "**8**" in report_text   # Tier 1 Arm N FPs
    assert "**5**" in report_text   # Tier 1 Arm R FPs
    assert "**6**" in report_text   # Tier 2 Arm N FPs
    assert "**3**" in report_text   # Tier 2 Arm R FPs
    assert "**-3 (-37.5%)**" in report_text
    assert "**-3 (-50.0%)**" in report_text
    assert "**-2 (-100%)**" in report_text
