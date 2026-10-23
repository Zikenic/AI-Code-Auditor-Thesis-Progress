"""Unit tests for context ablation ground truth adjudication and metrics integrity."""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
MANIFEST_PATH = REPO_ROOT / "data" / "ablation_adjudication_manifest.json"
CSV_PATH = REPO_ROOT / "data" / "results" / "context_ablation_pilot" / "finding_adjudication_table.csv"
PILOT_RESULTS_PATH = REPO_ROOT / "data" / "results" / "context_ablation_pilot" / "pilot_run" / "ablation_results.json"
SMOKE_RESULTS_PATH = REPO_ROOT / "data" / "results" / "context_ablation_pilot" / "smoke_test_run" / "ablation_results.json"


def test_adjudication_manifest_structure():
    """Verify adjudication manifest schema and complete fixture coverage."""
    assert MANIFEST_PATH.exists()
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert data["schema_version"] in ["1.0.0", "1.1.0", "1.2.0"]
    assert data["pilot_run_id"] == "ablation-run-1d21ebe5"
    fixtures = data["fixtures"]
    assert len(fixtures) == 6

    fixture_ids = [f["fixture_id"] for f in fixtures]
    assert fixture_ids == ["ABL-0001", "ABL-0002", "ABL-0003", "ABL-0004", "ABL-0005", "ABL-0006"]

    for f in fixtures:
        assert "intended_security_property" in f
        assert "actual_properties_supported" in f
        assert "concrete_source_locations" in f
        assert "verification_status" in f
        assert "categories" in f
        assert "clean_control_eligible" in f
        assert "adjudication_outcome" in f
        assert "confidence" in f
        assert "confidence_rationale" in f


def test_clean_control_eligibility_and_denominator():
    """Verify that only genuinely verified-clean fixtures are eligible as clean controls."""
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    fixtures = data["fixtures"]

    eligible = [f["fixture_id"] for f in fixtures if f["clean_control_eligible"]]
    ineligible = [f["fixture_id"] for f in fixtures if not f["clean_control_eligible"]]

    # Exactly 5 fixtures are eligible clean controls
    assert len(eligible) == 5
    assert eligible == ["ABL-0001", "ABL-0002", "ABL-0003", "ABL-0004", "ABL-0005"]

    # ABL-0006 is excluded due to confirmed reliability defects in key rotation and unhandled decode exceptions
    assert len(ineligible) == 1
    assert ineligible == ["ABL-0006"]
    abl006 = next(f for f in fixtures if f["fixture_id"] == "ABL-0006")
    assert abl006["adjudication_outcome"] == "mixed_defective_control"
    assert len(abl006["categories"]["correctness_defects"]) > 0 or len(abl006["categories"]["reliability_defects"]) > 0


def test_adjudication_finding_table_alignment():
    """Verify CSV finding adjudication table contains all 27 findings from canonical pilot results."""
    assert CSV_PATH.exists()
    assert PILOT_RESULTS_PATH.exists()

    pilot_data = json.loads(PILOT_RESULTS_PATH.read_text(encoding="utf-8"))
    raw_findings_count = sum(len(c["findings"]) for c in pilot_data["results"])
    assert raw_findings_count == 27

    with open(CSV_PATH, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    assert len(reader) == 27
    arm_n = [row for row in reader if row["arm"] == "Arm N"]
    arm_r = [row for row in reader if row["arm"] == "Arm R"]

    assert len(arm_n) == 14
    assert len(arm_r) == 13

    # Check finding IDs
    finding_ids = [row["finding_id"] for row in reader]
    assert len(set(finding_ids)) == 27


def test_adjudication_category_counts():
    """Verify exact distribution of adjudication categories across Arm N and Arm R."""
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    arm_n = [r for r in reader if r["arm"] == "Arm N"]
    arm_r = [r for r in reader if r["arm"] == "Arm R"]

    # 1. Confirmed security vulnerabilities
    sec_n = [r for r in arm_n if r["adjudication_category"] == "1_confirmed_vulnerability"]
    sec_r = [r for r in arm_r if r["adjudication_category"] == "1_confirmed_vulnerability"]
    assert len(sec_n) == 0
    assert len(sec_r) == 0

    # 2. Confirmed correctness / reliability defects
    rel_n = [r for r in arm_n if r["adjudication_category"] == "2_confirmed_correctness_reliability_defect"]
    rel_r = [r for r in arm_r if r["adjudication_category"] == "2_confirmed_correctness_reliability_defect"]
    assert len(rel_n) == 2  # ABL-0006-N-2 (decode error), ABL-0006-N-3 (key rotation)
    assert len(rel_r) == 2  # ABL-0006-R-2 (key rotation), ABL-0006-R-3 (decode error)

    # 3. False positives
    fp_n = [r for r in arm_n if r["adjudication_category"] == "4_false_positive"]
    fp_r = [r for r in arm_r if r["adjudication_category"] == "4_false_positive"]
    assert len(fp_n) == 10
    assert len(fp_r) == 7
    assert len(fp_r) < len(fp_n)  # Context arm reduced false positives by 3

    # 4. Plausible concerns
    pl_n = [r for r in arm_n if r["adjudication_category"] == "3_plausible_unconfirmed_concern"]
    pl_r = [r for r in arm_r if r["adjudication_category"] == "3_plausible_unconfirmed_concern"]
    assert len(pl_n) == 2
    assert len(pl_r) == 4


def test_clean_control_subset_metrics():
    """Verify metrics restricted to confirmed-clean control subset (ABL-0001 through ABL-0005)."""
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    clean_subset = [r for r in reader if r["fixture_id"] in ["ABL-0001", "ABL-0002", "ABL-0003", "ABL-0004", "ABL-0005"]]
    assert len(clean_subset) == 19  # 10 in Arm N, 9 in Arm R

    clean_n = [r for r in clean_subset if r["arm"] == "Arm N"]
    clean_r = [r for r in clean_subset if r["arm"] == "Arm R"]

    fp_clean_n = [r for r in clean_n if r["adjudication_category"] == "4_false_positive"]
    fp_clean_r = [r for r in clean_r if r["adjudication_category"] == "4_false_positive"]

    assert len(fp_clean_n) == 8
    assert len(fp_clean_r) == 5

    # ABL-0003 specific: false alarms dropped from 2 to 0
    abl3_n = [r for r in clean_n if r["fixture_id"] == "ABL-0003" and r["adjudication_category"] == "4_false_positive"]
    abl3_r = [r for r in clean_r if r["fixture_id"] == "ABL-0003"]
    assert len(abl3_n) == 2
    assert len(abl3_r) == 0


def test_smoke_test_telemetry_separation():
    """Verify smoke test run records are strictly separated and not recycled into pilot results."""
    assert SMOKE_RESULTS_PATH.exists()
    assert PILOT_RESULTS_PATH.exists()

    smoke = json.loads(SMOKE_RESULTS_PATH.read_text(encoding="utf-8"))
    pilot = json.loads(PILOT_RESULTS_PATH.read_text(encoding="utf-8"))

    # Different run IDs and timestamps
    assert smoke["metadata"]["run_id"] != pilot["metadata"]["run_id"]
    assert smoke["metadata"]["run_id"] == "ablation-run-5cc08b04"
    assert pilot["metadata"]["run_id"] == "ablation-run-1d21ebe5"

    # Slot counts differ
    assert len(smoke["results"]) == 2
    assert len(pilot["results"]) == 12

    # ABL-0001 in smoke run was re-executed independently in pilot run (distinct token counts & latencies)
    smoke_case_n = next(c for c in smoke["results"] if c["fixture_id"] == "ABL-0001" and c["arm"] == "N")
    pilot_case_n = next(c for c in pilot["results"] if c["fixture_id"] == "ABL-0001" and c["arm"] == "N")

    assert smoke_case_n["prompt_tokens"] != pilot_case_n["prompt_tokens"]
    assert smoke_case_n["duration_seconds"] != pilot_case_n["duration_seconds"]
