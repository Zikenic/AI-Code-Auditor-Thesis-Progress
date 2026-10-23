"""Comprehensive offline tests for Evaluation Harness, Metrics, and Manifest Contracts.

Validates:
1. Benchmark manifest loading and validation.
2. Clean, defective, and unknown case handling.
3. Matching logic and one-to-one consumption (preventing duplicate TP counts).
4. Precision, Recall, F1, and clean FPR calculations.
5. Incomplete / unknown labels excluded from metric denominators.
6. Partial and failed run tracking.
7. Config C static finding preservation and triage counts.
8. Config D comparison deltas over Config C.
9. Machine-readable JSON and CSV artifact generation.
10. Markdown evaluation report formatting.
11. Dry-run / offline mode independence from live APIs.
12. Live mode safety guard requiring explicit smoke-test opt-in.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from auditor.evaluation.manifest import (
    AnnotationCompleteness,
    AnnotationState,
    BenchmarkManifest,
    ManifestCase,
    load_benchmark_manifest,
)
from auditor.evaluation.metrics import (
    ConfigurationMetrics,
    compute_configuration_metrics,
)
from auditor.evaluation.report_generator import EvaluationReportGenerator
from auditor.evaluation.runner import EvaluationRunner
from auditor.models.finding import (
    DetectionLayer,
    PredictedFinding,
)


@pytest.fixture
def sample_manifest() -> BenchmarkManifest:
    """Provide synthetic benchmark manifest with defective, clean, and unknown cases."""
    case_buggy = ManifestCase(
        case_id="TEST-BUGGY-01",
        repository="org/repo",
        commit_hash="c111",
        target_file="app/auth.py",
        language="python",
        is_buggy=True,
        annotation_state=AnnotationState.VERIFIED,
        category_id=3,
        primary_cwe="CWE-89",
        acceptable_alternative_cwes=["CWE-20"],
        line_ranges=[[20, 25]],
        defects=[
            {
                "defect_id": "TEST-BUGGY-01-DEF-1",
                "category_id": 3,
                "primary_cwe": "CWE-89",
                "acceptable_alternative_cwes": ["CWE-20"],
                "file_path": "app/auth.py",
                "start_line": 20,
                "end_line": 25,
            }
        ],
    )

    case_clean = ManifestCase(
        case_id="TEST-CLEAN-01",
        repository="org/repo",
        commit_hash="c222",
        target_file="app/utils.py",
        language="python",
        is_buggy=False,
        annotation_state=AnnotationState.CLEAN,
        defects=[],
    )

    case_unknown = ManifestCase(
        case_id="TEST-UNKNOWN-01",
        repository="org/repo",
        commit_hash="c333",
        target_file="app/config.py",
        language="python",
        is_buggy=True,
        annotation_state=AnnotationState.UNKNOWN,
        defects=[],
    )

    return BenchmarkManifest(
        description="Synthetic Test Manifest",
        cases=[case_buggy, case_clean, case_unknown],
    )


# ---------------------------------------------------------------------------
# 1. Manifest Validation and Filtering
# ---------------------------------------------------------------------------
def test_manifest_case_classification(sample_manifest: BenchmarkManifest):
    buggy_cases = sample_manifest.get_verified_buggy_cases()
    clean_cases = sample_manifest.get_clean_cases()
    unknown_cases = sample_manifest.get_unknown_cases()

    assert len(buggy_cases) == 1
    assert buggy_cases[0].case_id == "TEST-BUGGY-01"

    assert len(clean_cases) == 1
    assert clean_cases[0].case_id == "TEST-CLEAN-01"

    assert len(unknown_cases) == 1
    assert unknown_cases[0].case_id == "TEST-UNKNOWN-01"


def test_manifest_rejects_inconsistent_annotations():
    with pytest.raises(ValueError, match="cannot have is_buggy=True and annotation_state=CLEAN"):
        ManifestCase(
            case_id="INVALID-01",
            repository="org/repo",
            commit_hash="c444",
            target_file="app.py",
            is_buggy=True,
            annotation_state=AnnotationState.CLEAN,
        )


# ---------------------------------------------------------------------------
# 2. Finding Matching & Duplicate Prevention
# ---------------------------------------------------------------------------
def test_duplicate_predictions_not_double_counted_as_tp(sample_manifest: BenchmarkManifest):
    # Two separate predictions for the same defect locus
    pred1 = PredictedFinding(
        finding_id="pred-1",
        detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
        tool_name="semgrep",
        category_id=3,
        primary_cwe="CWE-89",
        file_path="app/auth.py",
        start_line=21,
        end_line=24,
        title="SQLi 1",
        description="First prediction",
    )
    pred2 = PredictedFinding(
        finding_id="pred-2",
        detection_layer=DetectionLayer.HEURISTIC_LLM,
        tool_name="claude",
        category_id=3,
        primary_cwe="CWE-89",
        file_path="app/auth.py",
        start_line=22,
        end_line=25,
        title="SQLi 2",
        description="Duplicate prediction for same defect",
    )

    preds_by_case = {"TEST-BUGGY-01": [pred1, pred2]}
    metrics, details = compute_configuration_metrics("C", sample_manifest.cases, preds_by_case)

    # Must consume at most 1 TP via bipartite matching; second prediction is counted as FP
    assert metrics.true_positives == 1
    assert metrics.false_positives == 1
    assert metrics.false_negatives == 0
    assert metrics.precision == 0.5
    assert metrics.recall == 1.0


# ---------------------------------------------------------------------------
# 3. Precision / Recall / F1 / Clean-case FPR Calculations
# ---------------------------------------------------------------------------
def test_clean_case_fpr_and_precision_calculation(sample_manifest: BenchmarkManifest):
    # Pred on clean PR counts as FP
    pred_clean = PredictedFinding(
        finding_id="pred-clean",
        detection_layer=DetectionLayer.HEURISTIC_LLM,
        tool_name="claude",
        category_id=2,
        primary_cwe="CWE-20",
        file_path="app/utils.py",
        start_line=10,
        end_line=10,
        title="False warning on clean code",
        description="Hallucinated issue",
    )

    preds_by_case = {"TEST-CLEAN-01": [pred_clean]}
    metrics, _ = compute_configuration_metrics("B", sample_manifest.cases, preds_by_case)

    assert metrics.clean_cases_evaluated == 1
    assert metrics.clean_cases_flagged == 1
    assert metrics.clean_case_false_positive_rate == 1.0
    assert metrics.true_positives == 0
    assert metrics.false_positives == 1


# ---------------------------------------------------------------------------
# 4. Incomplete / Unknown Cases Excluded from GT Denominators
# ---------------------------------------------------------------------------
def test_unknown_case_exclusion_from_denominators(sample_manifest: BenchmarkManifest):
    pred_unknown = PredictedFinding(
        finding_id="pred-unk",
        detection_layer=DetectionLayer.HEURISTIC_LLM,
        tool_name="claude",
        category_id=1,
        primary_cwe="CWE-476",
        file_path="app/config.py",
        start_line=5,
        end_line=5,
        title="Null check",
        description="Potential null",
    )

    preds_by_case = {"TEST-UNKNOWN-01": [pred_unknown]}
    metrics, _ = compute_configuration_metrics("A", sample_manifest.cases, preds_by_case)

    assert metrics.unknown_cases_excluded == 1
    # Unknown case defects do not pollute verified ground truth total
    assert metrics.total_ground_truth_defects == 1  # Only from TEST-BUGGY-01


# ---------------------------------------------------------------------------
# 5. Config C Static Finding Preservation & Triage Metrics
# ---------------------------------------------------------------------------
def test_config_c_triage_metric_tracking(sample_manifest: BenchmarkManifest):
    pred_static_confirmed = PredictedFinding(
        finding_id="p-stat-1",
        detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
        tool_name="semgrep",
        category_id=3,
        primary_cwe="CWE-89",
        file_path="app/auth.py",
        start_line=20,
        end_line=22,
        title="Real SQLi",
        description="Confirmed flaw",
        provenance={"triage": "confirmed"},
    )
    pred_static_fp = PredictedFinding(
        finding_id="p-stat-2",
        detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
        tool_name="ruff",
        category_id=2,
        primary_cwe="CWE-20",
        file_path="app/auth.py",
        start_line=50,
        end_line=50,
        title="Lint rule",
        description="Likely FP",
        provenance={"triage": "likely_false_positive"},
    )
    pred_additional = PredictedFinding(
        finding_id="p-llm-1",
        detection_layer=DetectionLayer.HEURISTIC_LLM,
        tool_name="claude",
        category_id=5,
        primary_cwe="CWE-287",
        file_path="app/auth.py",
        start_line=80,
        end_line=82,
        title="Novel bug",
        description="Additional defect",
    )

    preds_by_case = {"TEST-BUGGY-01": [pred_static_confirmed, pred_static_fp, pred_additional]}
    metrics, _ = compute_configuration_metrics("C", sample_manifest.cases, preds_by_case)

    assert metrics.static_findings_total == 2
    assert metrics.static_findings_preserved == 2
    assert metrics.static_findings_confirmed == 1
    assert metrics.static_findings_likely_fp == 1
    assert metrics.additional_llm_candidates == 1
    assert metrics.triage_correct_fp_count == 1  # p-stat-2 at line 50 was NOT in GT locus (20-25)


# ---------------------------------------------------------------------------
# 6. Config D Incremental Comparisons vs Config C
# ---------------------------------------------------------------------------
def test_config_d_incremental_delta_calculation(sample_manifest: BenchmarkManifest):
    baseline_c = ConfigurationMetrics(
        configuration="C",
        true_positives=8,
        false_positives=87,
    )

    preds_d = {
        "TEST-BUGGY-01": [
            PredictedFinding(
                finding_id="d-1",
                detection_layer=DetectionLayer.HEURISTIC_LLM,
                tool_name="claude",
                category_id=3,
                primary_cwe="CWE-89",
                file_path="app/auth.py",
                start_line=20,
                end_line=25,
                title="Matched defect",
                description="Matched",
            )
        ]
    }

    metrics_d, _ = compute_configuration_metrics(
        "D", sample_manifest.cases, preds_d, config_c_baseline=baseline_c
    )

    # D had 1 TP vs C's 8 TPs -> delta is -7
    assert metrics_d.incremental_tp_over_c == -7
    # D had 0 FPs vs C's 87 FPs -> delta is -87
    assert metrics_d.incremental_fp_over_c == -87


# ---------------------------------------------------------------------------
# 7. Machine-Readable Export (JSON & CSV) and Markdown Report
# ---------------------------------------------------------------------------
def test_report_artifact_generation(sample_manifest: BenchmarkManifest, tmp_path: Path):
    metrics_a = ConfigurationMetrics(configuration="A", true_positives=3, false_positives=126, false_negatives=20)
    metrics_c = ConfigurationMetrics(configuration="C", true_positives=8, false_positives=87, false_negatives=15)

    rep_gen = EvaluationReportGenerator(
        manifest=sample_manifest,
        metrics_by_config={"A": metrics_a, "C": metrics_c},
        details_by_config={"A": [], "C": []},
        run_metadata={"mode": "offline", "commit_hash": "testcommit"},
    )

    json_file = rep_gen.generate_json_artifact(tmp_path / "summary.json")
    csv_file = rep_gen.generate_csv_summary(tmp_path / "summary.csv")
    md_file = rep_gen.generate_markdown_report(tmp_path / "report.md")

    assert json_file.exists()
    assert csv_file.exists()
    assert md_file.exists()

    # Validate JSON structure
    with open(json_file, encoding="utf-8") as f:
        data = json.load(f)
    assert "configurations" in data
    assert "Config A" in data["configurations"]["A"]["configuration"] or data["configurations"]["A"]["configuration"] == "A"

    # Validate CSV content
    with open(csv_file, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 2
    assert reader[0]["Configuration"] == "Config A"

    # Validate Markdown content
    md_text = md_file.read_text(encoding="utf-8")
    assert "# AI Code Auditor" in md_text
    assert "Config A (Static)" in md_text
    assert "Configuration C Detailed Triage Analysis" in md_text


# ---------------------------------------------------------------------------
# 8. Dry-Run Offline Independence
# ---------------------------------------------------------------------------
def test_evaluation_runner_offline_mode(sample_manifest: BenchmarkManifest):
    runner = EvaluationRunner(manifest=sample_manifest, mode="offline", use_frozen_fixture_fallback=False)
    # Offline mode executes without throwing network / missing credentials errors
    out = runner.run_configuration("A", case_ids=["TEST-BUGGY-01"])
    assert out.configuration == "A"
    assert "TEST-BUGGY-01" in out.predictions_by_case


# ---------------------------------------------------------------------------
# 9. Ground-Truth Completeness & Clean Controls Validation
# ---------------------------------------------------------------------------
def test_manifest_completeness_states_and_validation():
    """Verify AnnotationCompleteness states and clean case invariant."""
    case = ManifestCase(
        case_id="CTRL-TEST-01",
        repository="local/controls",
        commit_hash="h1",
        target_file="test.py",
        is_buggy=False,
        annotation_state=AnnotationState.CLEAN,
        annotation_completeness=AnnotationCompleteness.EXHAUSTIVE,
        reviewed_categories=[1, 2],
        target_scope="Full function test",
    )
    assert case.annotation_completeness == AnnotationCompleteness.EXHAUSTIVE
    assert case.is_buggy is False
    bcase = case.to_benchmark_case()
    assert bcase.annotation_completeness == "exhaustive"
    assert len(bcase.defects) == 0


def test_stable_ids_and_non_colliding_clean_controls():
    """Verify 100 distinct cases in benchmark_manifest.json with zero ID collisions."""
    repo_root = Path(__file__).resolve().parents[1]
    manifest = load_benchmark_manifest(repo_root / "data" / "benchmark_manifest.json")

    assert len(manifest.cases) == 100
    case_ids = [c.case_id for c in manifest.cases]
    assert len(set(case_ids)) == 100

    buggy_ids = {c.case_id for c in manifest.cases if c.is_buggy}
    clean_ids = {c.case_id for c in manifest.cases if not c.is_buggy}
    assert len(buggy_ids) == 50
    assert len(clean_ids) == 50
    assert buggy_ids.isdisjoint(clean_ids)

    # Verify all 50 clean control fixture files exist on disk
    for c in manifest.cases:
        if not c.is_buggy and c.fixture_path:
            assert (repo_root / c.fixture_path).exists(), f"Missing fixture file: {c.fixture_path}"

    # Verify all 32 expanded buggy fixture files exist on disk
    for c in manifest.cases:
        if c.is_buggy and c.fixture_path:
            assert (repo_root / c.fixture_path).exists(), f"Missing fixture file: {c.fixture_path}"


def test_clean_control_fixtures_exist_and_pass_static_analysis():
    """Verify clean control fixtures exist on disk and emit zero static alerts."""
    from auditor.static_analysis.engine import StaticAnalysisEngine

    repo_root = Path(__file__).resolve().parents[1]
    fixtures_dir = repo_root / "data" / "fixtures" / "clean_controls"
    assert fixtures_dir.exists()

    engine = StaticAnalysisEngine()
    findings = engine.run_static_analysis(
        workspace_path=str(fixtures_dir),
        changed_files=["ctrl_0001_http_chunking.py", "ctrl_0004_form_csrf.py"],
    )
    assert len(findings) == 0


def test_clean_case_fpr_calculation_and_zero_clean_denominator():
    """Verify clean-case FPR formula and zero clean denominator handling."""
    clean_case = ManifestCase(
        case_id="CTRL-01",
        repository="local/c",
        commit_hash="h",
        target_file="f.py",
        is_buggy=False,
        annotation_state=AnnotationState.CLEAN,
        annotation_completeness=AnnotationCompleteness.EXHAUSTIVE,
    )

    # 1. Zero predictions -> Clean FPR = 0.0%
    m1, _ = compute_configuration_metrics("A", [clean_case], {"CTRL-01": []})
    assert m1.clean_case_false_positive_rate == 0.0
    assert m1.clean_cases_flagged == 0
    assert m1.clean_cases_successful == 1

    # 2. Flagged clean case -> Clean FPR = 100.0%
    pred = PredictedFinding(
        finding_id="fp-1",
        detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
        tool_name="ruff",
        category_id=1,
        primary_cwe="CWE-670",
        file_path="f.py",
        start_line=10,
        end_line=10,
        title="FP alert",
        description="False positive",
    )
    m2, _ = compute_configuration_metrics("A", [clean_case], {"CTRL-01": [pred]})
    assert m2.clean_case_false_positive_rate == 1.0
    assert m2.clean_cases_flagged == 1
    assert m2.confirmed_false_positives == 1

    # 3. Zero clean cases in dataset -> Clean FPR is None (undefined)
    buggy_only = ManifestCase(
        case_id="BUGGY-01",
        repository="r",
        commit_hash="h",
        target_file="f.py",
        is_buggy=True,
        annotation_state=AnnotationState.VERIFIED,
        category_id=1,
        primary_cwe="CWE-670",
        line_ranges=[[5, 5]],
    )
    m3, _ = compute_configuration_metrics("A", [buggy_only], {"BUGGY-01": []})
    assert m3.clean_case_false_positive_rate is None


def test_partial_annotations_record_unadjudicated_findings():
    """Ensure unmatched predictions on partial cases are classified as unadjudicated."""
    partial_buggy = ManifestCase(
        case_id="CAND-TEST",
        repository="r",
        commit_hash="h",
        target_file="f.py",
        is_buggy=True,
        annotation_state=AnnotationState.VERIFIED,
        annotation_completeness=AnnotationCompleteness.PARTIAL,
        category_id=1,
        primary_cwe="CWE-670",
        line_ranges=[[10, 10]],
    )

    # Prediction far from GT locus (line 50 vs GT line 10)
    unmatched_pred = PredictedFinding(
        finding_id="cand-pred-1",
        detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
        tool_name="ruff",
        category_id=1,
        primary_cwe="CWE-670",
        file_path="f.py",
        start_line=50,
        end_line=50,
        title="Unmatched finding",
        description="Unadjudicated",
    )

    m, details = compute_configuration_metrics("A", [partial_buggy], {"CAND-TEST": [unmatched_pred]})
    # On a partial case, unmatched prediction is recorded as unadjudicated, NOT confirmed FP
    assert m.confirmed_false_positives == 0
    assert m.unadjudicated_predictions == 1
    assert details[0].confirmed_false_positives == 0
    assert details[0].unadjudicated_predictions == 1


def test_common_subset_comparison_across_configurations():
    """Verify common subset metric computation on paired subset."""
    case1 = ManifestCase(
        case_id="CASE-1",
        repository="r",
        commit_hash="h",
        target_file="f.py",
        is_buggy=True,
        category_id=1,
        primary_cwe="CWE-670",
        line_ranges=[[10, 10]],
    )
    case2 = ManifestCase(
        case_id="CASE-2",
        repository="r",
        commit_hash="h",
        target_file="f.py",
        is_buggy=True,
        category_id=1,
        primary_cwe="CWE-670",
        line_ranges=[[20, 20]],
    )

    matched_p = PredictedFinding(
        finding_id="p-1",
        detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
        tool_name="ruff",
        category_id=1,
        primary_cwe="CWE-670",
        file_path="f.py",
        start_line=10,
        end_line=10,
        title="T",
        description="D",
    )

    m, _ = compute_configuration_metrics(
        "A",
        [case1, case2],
        {"CASE-1": [matched_p], "CASE-2": []},
        common_case_ids={"CASE-1"},
    )

    assert m.common_subset_metrics is not None
    assert m.common_subset_metrics["cases_count"] == 1
    assert m.common_subset_metrics["true_positives"] == 1
    assert m.common_subset_metrics["false_negatives"] == 0


def test_historical_preservation_intact():
    """Assert historical artifacts remain preserved and unmodified."""
    repo_root = Path(__file__).resolve().parents[1]
    archive_dir = repo_root / "data" / "results" / "historical_18_case_eval"
    assert archive_dir.exists()
    assert (archive_dir / "evaluation_summary.json").exists()
    assert (archive_dir / "evaluation_summary.csv").exists()
    assert (archive_dir / "evaluation_report.md").exists()
    assert (repo_root / "Project Documents" / "reports" / "historical_18_case_evaluation_report.md").exists()
    assert (repo_root / "data" / "pilot_cases.json").exists()


def test_mock_clean_controls_cannot_establish_empirical_fpr():
    """Assert that clean controls run with mock LLM outputs cannot establish empirical model FPR."""
    clean_case = ManifestCase(
        case_id="CTRL-TEST-01",
        repository="org/repo",
        commit_hash="h111",
        target_file="clean.py",
        is_buggy=False,
        annotation_state=AnnotationState.CLEAN,
        annotation_completeness=AnnotationCompleteness.EXHAUSTIVE,
        defects=[],
    )

    prov_map = {
        "CTRL-TEST-01": {
            "source": "mock",
            "model": "MockEvaluationLlmClient",
            "status": "success",
        }
    }

    m, details = compute_configuration_metrics(
        configuration="B",
        manifest_cases=[clean_case],
        predictions_by_case={"CTRL-TEST-01": []},
        provenance_by_case=prov_map,
    )

    assert m.clean_cases_mocked_count == 1
    assert m.clean_case_false_positive_rate is None
    assert m.clean_case_fpr_status == "unavailable_mock"
    assert "Mock results cannot establish empirical model false-positive rate" in m.clean_case_fpr_note
    assert m.is_mock_evaluation is True
    assert details[0].metric_eligibility["clean_fpr"] is False
    assert "Mock outputs cannot be used to establish empirical model false-positive rate" in details[0].exclusion_reasons["clean_fpr"]


def test_deterministic_clean_controls_eligible_for_fpr():
    """Assert that deterministic static analysis on clean controls is eligible for observed FPR."""
    clean_case = ManifestCase(
        case_id="CTRL-TEST-02",
        repository="org/repo",
        commit_hash="h222",
        target_file="clean2.py",
        is_buggy=False,
        annotation_state=AnnotationState.CLEAN,
        annotation_completeness=AnnotationCompleteness.EXHAUSTIVE,
        defects=[],
    )

    prov_map = {
        "CTRL-TEST-02": {
            "source": "real_deterministic",
            "model": "Ruff + Semgrep",
            "status": "success",
        }
    }

    m, details = compute_configuration_metrics(
        configuration="A",
        manifest_cases=[clean_case],
        predictions_by_case={"CTRL-TEST-02": []},
        provenance_by_case=prov_map,
    )

    assert m.clean_cases_mocked_count == 0
    assert m.clean_case_false_positive_rate == 0.0
    assert m.clean_case_fpr_status == "eligible"
    assert details[0].metric_eligibility["clean_fpr"] is True


def test_provenance_classification_rules():
    """Assert determine_case_eligibility accurately classifies provenance constraints."""
    from auditor.evaluation.provenance import ResultProvenance, determine_case_eligibility

    # Mock cannot establish recall or clean FPR
    elig_mock, excl_mock = determine_case_eligibility(
        provenance=ResultProvenance.MOCK,
        is_buggy=True,
        status="success",
    )
    assert elig_mock["recall"] is False
    assert "Mock outputs cannot be used for empirical defect recall" in excl_mock["recall"]

    elig_mock_clean, excl_mock_clean = determine_case_eligibility(
        provenance=ResultProvenance.MOCK,
        is_buggy=False,
        status="success",
    )
    assert elig_mock_clean["clean_fpr"] is False
    assert "Mock outputs cannot be used to establish empirical model false-positive rate" in excl_mock_clean["clean_fpr"]

    # Real deterministic can establish clean FPR
    elig_det, _ = determine_case_eligibility(
        provenance=ResultProvenance.REAL_DETERMINISTIC,
        is_buggy=False,
        status="success",
    )
    assert elig_det["clean_fpr"] is True


def test_report_generator_isolates_mock_clean_fpr(tmp_path: Path):
    """Assert report generator isolates mock validation from empirical accuracy in CSV and MD."""
    clean_case = ManifestCase(
        case_id="CTRL-TEST-03",
        repository="org/repo",
        commit_hash="h333",
        target_file="clean3.py",
        is_buggy=False,
        annotation_state=AnnotationState.CLEAN,
        annotation_completeness=AnnotationCompleteness.EXHAUSTIVE,
        defects=[],
    )
    manifest = BenchmarkManifest(description="T", cases=[clean_case])

    # Config A: real deterministic
    mA, detA = compute_configuration_metrics(
        "A", [clean_case], {"CTRL-TEST-03": []},
        provenance_by_case={"CTRL-TEST-03": {"source": "real_deterministic", "status": "success"}}
    )
    # Config B: mock
    mB, detB = compute_configuration_metrics(
        "B", [clean_case], {"CTRL-TEST-03": []},
        provenance_by_case={"CTRL-TEST-03": {"source": "mock", "status": "success"}}
    )

    rep_gen = EvaluationReportGenerator(
        manifest=manifest,
        metrics_by_config={"A": mA, "B": mB},
        details_by_config={"A": detA, "B": detB},
    )

    csv_file = rep_gen.generate_csv_summary(tmp_path / "test_summary.csv")
    md_file = rep_gen.generate_markdown_report(tmp_path / "test_report.md")

    # Inspect CSV
    with open(csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = {r["Configuration"]: r for r in reader}
        assert rows["Config A"]["Clean Case FPR"] == "0.00%"
        assert rows["Config A"]["Clean Case FPR Status"] == "eligible"
        assert rows["Config B"]["Clean Case FPR"] == "Unavailable (mock LLM)"
        assert rows["Config B"]["Clean Case FPR Status"] == "unavailable_mock"

    # Inspect MD
    md_text = md_file.read_text(encoding="utf-8")
    assert "**Unavailable** *(mock LLM client)*" in md_text
    assert "**0.00%** *(curated sample)*" in md_text
    assert "## 6. Case-by-Case Provenance & Metric Eligibility Matrix" in md_text


def test_runner_config_d_dispatch_and_execution(tmp_path: Path):
    """Verify that EvaluationRunner correctly dispatches Config D and handles context."""
    from auditor.evaluation.runner import MockEvaluationLlmClient

    case = ManifestCase(
        case_id="CTRL-D-01",
        repository="local/test",
        commit_hash="00000000",
        target_file="ctrl_0001_http_chunking.py",
        is_buggy=False,
        annotation_state=AnnotationState.CLEAN,
        annotation_completeness=AnnotationCompleteness.EXHAUSTIVE,
        defects=[],
    )
    manifest = BenchmarkManifest(description="T", cases=[case])

    mock_client = MockEvaluationLlmClient()
    runner = EvaluationRunner(
        manifest=manifest,
        mode="offline",
        api_client=mock_client,
    )

    # Directly verify run_case_config_d
    status, findings, dur, meta = runner.run_case_config_d(case, tmp_path, [])
    assert isinstance(findings, list)
    assert status.value == "success" if hasattr(status, "value") else str(status) == "success"

    # Verify run_configuration("D") dispatches properly
    output = runner.run_configuration("D")
    assert output.configuration == "D"
    assert "CTRL-D-01" in output.predictions_by_case
    assert output.statuses_by_case["CTRL-D-01"] == "success"
    assert output.provenance_by_case["CTRL-D-01"]["source"] == "mock"


def test_clean_cohort_separation_report_rendering(tmp_path: Path):
    """Verify that EvaluationReportGenerator separates clean cohort from historical defect baseline."""
    clean_case = ManifestCase(
        case_id="CTRL-SEP-01",
        repository="local/clean",
        commit_hash="00000000",
        target_file="clean.py",
        is_buggy=False,
        annotation_state=AnnotationState.CLEAN,
        annotation_completeness=AnnotationCompleteness.EXHAUSTIVE,
        defects=[],
    )
    manifest = BenchmarkManifest(description="Clean Only Cohort", cases=[clean_case])

    mA, detA = compute_configuration_metrics(
        "A", [clean_case], {"CTRL-SEP-01": []},
        provenance_by_case={"CTRL-SEP-01": {"source": "real_deterministic", "status": "success"}}
    )
    mB, detB = compute_configuration_metrics(
        "B", [clean_case], {"CTRL-SEP-01": []},
        provenance_by_case={"CTRL-SEP-01": {"source": "real_model", "status": "success"}}
    )

    generator = EvaluationReportGenerator(
        manifest=manifest,
        metrics_by_config={"A": mA, "B": mB},
        details_by_config={"A": detA, "B": detB},
    )

    md_out = tmp_path / "clean_sep_report.md"
    generator.generate_markdown_report(md_out)
    content = md_out.read_text(encoding="utf-8")

    assert "## 4. Defective Pilot Cohort vs Clean Control Separation" in content
    assert "15.79%** (3/19)" in content
    assert "36.84%** (7/19)" in content
    assert "Observed Clean-Control Findings (Unadjudicated)" in content
    assert "Clean-Control Case Alert Rate" in content




