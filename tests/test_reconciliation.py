"""Focused offline unit tests for Phase 5D reconciliation tools."""

from __future__ import annotations

from pathlib import Path

from tools.generate_adjudication_packet_bcd_v2 import generate_packet_v2
from tools.print_abcd_rows import run_reconciliation

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_reconciliation_audit_structure():
    """Verify that run_reconciliation produces auditable per-case rows with 100% parity."""
    data = run_reconciliation()

    assert "per_case_audit" in data
    assert "primary_aggregates" in data
    assert "paired_17_cases" in data
    assert "common_completed_subset" in data
    assert "per_category_reconciliation" in data

    rows = data["per_case_audit"]
    assert len(rows) == 18

    # Verify parity across all cases and configs
    for r in rows:
        for cfg_label, info in r["configurations"].items():
            assert info["match_parity"] is True, f"Parity mismatch in {r['case_id']} {cfg_label}"


def test_primary_aggregate_totals_match():
    """Verify that primary aggregate totals match the frozen benchmark results exactly."""
    data = run_reconciliation()
    aggs = data["primary_aggregates"]

    # Config A
    assert aggs["Config A"]["tp"] == 3
    assert aggs["Config A"]["fp"] == 126
    assert aggs["Config A"]["fn"] == 20

    # Config B
    assert aggs["Config B"]["tp"] == 6
    assert aggs["Config B"]["fp"] == 94
    assert aggs["Config B"]["fn"] == 17

    # Config C
    assert aggs["Config C"]["tp"] == 8
    assert aggs["Config C"]["fp"] == 87
    assert aggs["Config C"]["fn"] == 15

    # Config D
    assert aggs["Config D"]["tp"] == 7
    assert aggs["Config D"]["fp"] == 85
    assert aggs["Config D"]["fn"] == 16


def test_paired_17_case_and_common_completed_subset():
    """Verify subset calculations: 17-case paired B vs C and 14-case common completed."""
    data = run_reconciliation()

    # Paired 17
    p17 = data["paired_17_cases"]
    assert len(p17["included_case_ids"]) == 17
    assert "CAND-0008" not in p17["included_case_ids"]
    assert p17["Config B"]["fp"] == 79
    assert p17["Config C"]["fp"] == 87

    # Common 14
    ccs = data["common_completed_subset"]
    assert len(ccs["included_case_ids"]) == 14
    assert ccs["Config B"]["fp"] == 60
    assert ccs["Config C"]["fp"] == 66
    assert ccs["Config D"]["fp"] == 69
    assert ccs["Config C"]["tp"] == 7
    assert ccs["Config D"]["tp"] == 7


def test_adjudication_packet_v2_generation():
    """Verify that generate_packet_v2 generates valid B/C/D packet without Config A."""
    packet = generate_packet_v2()

    assert packet["metadata"]["total_unique_gt_defects"] == 9
    assert packet["metadata"]["total_matched_rows"] == 21
    assert packet["metadata"]["config_counts"]["Config B"] == 6
    assert packet["metadata"]["config_counts"]["Config C"] == 8
    assert packet["metadata"]["config_counts"]["Config D"] == 7

    for d in packet["grouped_defects"]:
        assert "Config A" not in d["matching_configurations"]
        for m in d["matches"]:
            assert m["config"] in ["Config B", "Config C", "Config D"]
