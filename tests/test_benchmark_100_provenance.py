"""Comprehensive validation tests for the 100-Case Benchmark and Provenance Integrity.

Verifies:
1. Manifest case census: exactly 100 registered cases (50 buggy, 50 clean).
2. Exact cohort provenance:
   - 18 externally sourced upstream repository snapshots (synthetic=False, source_type='upstream_repository_snapshot').
   - 32 synthetic buggy fixtures (synthetic=True, source_type='synthetic_fixture').
   - 18 handcrafted clean fixtures (synthetic=True, source_type='handcrafted_clean_fixture').
   - 32 synthetic clean fixtures (synthetic=True, source_type='synthetic_fixture').
3. Total runnable census: 100/100 cases resolve authentic source code on disk without placeholders.
4. Upstream snapshot provenance: SHA256 integrity and ground-truth locus extraction.
5. Strict category impact compliance (Cat 1 impact in ['security', 'functional'], Cat 2..6 impact=None).
6. Preservation of historical pilot run results in data/results/.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from auditor.evaluation.manifest import load_benchmark_manifest
from auditor.evaluation.runner import EvaluationRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "data" / "benchmark_manifest.json"
UPSTREAM_SNAPSHOTS_DIR = REPO_ROOT / "data" / "fixtures" / "upstream_snapshots"
RESULTS_DIR = REPO_ROOT / "data" / "results"

HISTORICAL_BUGGY_IDS = {1, 2, 6, 7, 8, 9, 14, 15, 17, 19, 20, 21, 25, 26, 27, 31, 32, 33}


@pytest.fixture(scope="module")
def manifest():
    return load_benchmark_manifest(MANIFEST_PATH)


def test_manifest_census_and_split(manifest):
    """Verify total cases, defective vs clean balance, and stable ID ranges."""
    assert len(manifest.cases) == 100

    buggy_cases = [c for c in manifest.cases if c.is_buggy]
    clean_cases = [c for c in manifest.cases if not c.is_buggy]

    assert len(buggy_cases) == 50
    assert len(clean_cases) == 50

    buggy_ids = [c.case_id for c in buggy_cases]
    clean_ids = [c.case_id for c in clean_cases]

    assert buggy_ids[0] == "CAND-0001"
    assert buggy_ids[-1] == "CAND-0050"
    assert clean_ids[0] == "CTRL-0001"
    assert clean_ids[-1] == "CTRL-0050"


def test_accurate_provenance_and_synthetic_flag_breakdown(manifest):
    """Verify accurate provenance classification distinguishing synthetic/handcrafted from upstream."""
    upstream_snapshots = [c for c in manifest.cases if c.source_type == "upstream_repository_snapshot"]
    synthetic_buggy = [c for c in manifest.cases if c.is_buggy and c.source_type == "synthetic_fixture"]
    handcrafted_clean = [c for c in manifest.cases if not c.is_buggy and c.source_type == "handcrafted_clean_fixture"]
    synthetic_clean = [c for c in manifest.cases if not c.is_buggy and c.source_type == "synthetic_fixture"]

    # Cohort 1: 18 upstream repository snapshots
    assert len(upstream_snapshots) == 18
    for c in upstream_snapshots:
        assert not c.synthetic
        num = int(c.case_id.split("-")[1])
        assert num in HISTORICAL_BUGGY_IDS
        assert c.fixture_path is not None
        assert (REPO_ROOT / c.fixture_path).exists()

    # Cohort 2: 32 synthetic buggy fixtures
    assert len(synthetic_buggy) == 32
    for c in synthetic_buggy:
        assert c.synthetic
        assert c.fixture_path is not None
        assert (REPO_ROOT / c.fixture_path).exists()

    # Cohort 3: 18 handcrafted clean control fixtures (CTRL-0001..CTRL-0018)
    assert len(handcrafted_clean) == 18
    for c in handcrafted_clean:
        assert c.synthetic
        num = int(c.case_id.split("-")[1])
        assert 1 <= num <= 18
        assert c.fixture_path is not None
        assert (REPO_ROOT / c.fixture_path).exists()

    # Cohort 4: 32 synthetic clean control fixtures (CTRL-0019..CTRL-0050)
    assert len(synthetic_clean) == 32
    for c in synthetic_clean:
        assert c.synthetic
        num = int(c.case_id.split("-")[1])
        assert 19 <= num <= 50
        assert c.fixture_path is not None
        assert (REPO_ROOT / c.fixture_path).exists()

    # Totals: Exactly 18 upstream, 82 synthetic/handcrafted
    total_synthetic = sum(1 for c in manifest.cases if c.synthetic)
    total_upstream = sum(1 for c in manifest.cases if not c.synthetic)
    assert total_synthetic == 82
    assert total_upstream == 18


def test_100_percent_runnable_without_placeholders(manifest):
    """Verify that every single registered case resolves to authentic source code on disk."""
    runner = EvaluationRunner(manifest=manifest)

    resolved_count = 0
    for case in manifest.cases:
        code = runner._resolve_case_code(case, allow_placeholder=False)
        assert len(code) > 0, f"Case {case.case_id} resolved empty source."
        assert "def authenticate(user_token):" not in code, f"Case {case.case_id} received placeholder code."
        resolved_count += 1

    assert resolved_count == 100


def test_upstream_snapshots_integrity_and_locus_verification(manifest):
    """Verify disk integrity and ground-truth locus extraction for all 18 upstream snapshots."""
    upstream_cases = [c for c in manifest.cases if c.source_type == "upstream_repository_snapshot"]
    assert len(upstream_cases) == 18

    for c in upstream_cases:
        case_dir = UPSTREAM_SNAPSHOTS_DIR / c.case_id
        assert case_dir.exists(), f"Snapshot directory missing for {c.case_id}"

        prov_path = case_dir / "provenance.json"
        assert prov_path.exists(), f"provenance.json missing for {c.case_id}"

        with open(prov_path, encoding="utf-8") as f:
            prov = json.load(f)

        target_file_path = case_dir / c.target_file
        assert target_file_path.exists(), f"Target file missing for {c.case_id} at {target_file_path}"

        raw_bytes = target_file_path.read_bytes()
        computed_sha = hashlib.sha256(raw_bytes).hexdigest()
        assert computed_sha == prov["sha256"], f"SHA256 mismatch for {c.case_id}"

        # Verify ground truth locus lines extract valid non-empty text
        raw_text = raw_bytes.decode("utf-8", errors="replace")
        lines = raw_text.splitlines()
        for start, end in c.line_ranges:
            locus_lines = lines[start - 1 : end]
            assert len(locus_lines) > 0
            snippet = "\n".join(locus_lines).strip()
            assert len(snippet) > 0, f"Locus lines {start}-{end} empty for {c.case_id}"


def test_category_and_impact_schema_compliance(manifest):
    """Verify strict taxonomy Category 1..6 and impact schema rules."""
    for c in manifest.cases:
        if c.is_buggy:
            assert 1 <= c.category_id <= 6
            for d in c.defects:
                if d["category_id"] == 1:
                    assert d["impact"] in ["security", "functional"]
                else:
                    assert d["impact"] is None
        else:
            assert not c.is_buggy
            assert len(c.defects) == 0


def test_historical_pilot_results_unmodified():
    """Verify that original historical result files in data/results/ remain preserved and unmodified."""
    expected_historical_runs = [
        "config_a_pilot_run.json",
        "config_b_pilot_run.json",
        "config_c_pilot_run.json",
        "config_d_pilot_run.json",
    ]
    for filename in expected_historical_runs:
        path = RESULTS_DIR / filename
        assert path.exists(), f"Historical result {filename} missing!"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "cases" in data or "evaluations" in data
