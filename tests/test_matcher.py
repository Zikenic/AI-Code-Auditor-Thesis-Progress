"""Unit tests for offline evaluation benchmark matcher, range matching, and scoring rules."""

import random

import pytest

from auditor.matcher.engine import OfflineEvaluationMatcher
from auditor.matcher.location import (
    check_location_match,
    has_direct_overlap,
)
from auditor.models.finding import DetectionLayer, PredictedFinding
from auditor.models.ground_truth import BenchmarkCase, GroundTruthDefect
from auditor.models.result import EvaluationMetrics


@pytest.fixture
def sample_defect():
    return GroundTruthDefect(
        defect_id="DEF-001",
        category_id=3,
        primary_cwe="CWE-89",
        acceptable_alternative_cwes={"CWE-20"},
        file_path="src/database/query.py",
        start_line=50,
        end_line=50,
        description="SQL injection via string formatting",
    )


def make_finding(
    finding_id="FIND-01",
    file_path="src/database/query.py",
    start_line=50,
    end_line=50,
    primary_cwe="CWE-89",
    category_id=3,
):
    return PredictedFinding(
        finding_id=finding_id,
        detection_layer=DetectionLayer.HEURISTIC_LLM,
        tool_name="gemini-1.5-pro",
        category_id=category_id,
        primary_cwe=primary_cwe,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        title="Test finding",
        description="Test finding description",
    )


class TestLocationBoundaryLogic:
    def test_direct_overlap(self):
        # Exact line
        assert has_direct_overlap(50, 50, 50, 50) is True
        # Partial range overlap
        assert has_direct_overlap(50, 55, 45, 52) is True
        assert has_direct_overlap(50, 55, 53, 60) is True
        # No overlap
        assert has_direct_overlap(50, 55, 40, 49) is False
        assert has_direct_overlap(50, 55, 56, 60) is False

    def test_exact_plus_minus_10_and_11_boundaries(self):
        # GT is at line 50. Tolerance window is [40, 60].
        # Exact lower boundary: line 40 (distance -10) -> ACCEPTED
        matched, direct = check_location_match(50, 50, 40, 40, tolerance=10)
        assert matched is True
        assert direct is False

        # One line beyond lower boundary: line 39 (distance -11) -> REJECTED
        matched, direct = check_location_match(50, 50, 39, 39, tolerance=10)
        assert matched is False

        # Exact upper boundary: line 60 (distance +10) -> ACCEPTED
        matched, direct = check_location_match(50, 50, 60, 60, tolerance=10)
        assert matched is True
        assert direct is False

        # One line beyond upper boundary: line 61 (distance +11) -> REJECTED
        matched, direct = check_location_match(50, 50, 61, 61, tolerance=10)
        assert matched is False

    def test_multi_line_findings(self):
        # GT is [50, 55]. Window is [40, 65].
        # Multi-line overlapping GT: [45, 52] -> ACCEPTED, direct overlap
        matched, direct = check_location_match(50, 55, 45, 52)
        assert matched is True
        assert direct is True

        # Multi-line not overlapping GT directly, but intersecting tolerance window [35, 42]
        # Intersects [40, 65] at lines 40-42 -> ACCEPTED, not direct overlap
        matched, direct = check_location_match(50, 55, 35, 42)
        assert matched is True
        assert direct is False

        # Multi-line completely outside window: [20, 38] -> REJECTED
        matched, direct = check_location_match(50, 55, 20, 38)
        assert matched is False

    def test_missing_or_invalid_coordinates(self):
        # None coordinates
        matched, _ = check_location_match(50, 50, None, None)
        assert matched is False

        # Start line only without end line handled by check_location_match
        matched, _ = check_location_match(50, 50, 50, None)
        assert matched is False

        # Invalid line coordinates (< 1)
        matched, _ = check_location_match(50, 50, 0, 0)
        assert matched is False
        matched, _ = check_location_match(50, 50, -5, 10)
        assert matched is False


class TestOfflineEvaluationMatcher:
    def test_exact_match_yields_perfect_score(self, sample_defect):
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)
        case = BenchmarkCase(
            case_id="BUG-001",
            repository="owner/repo",
            commit_hash="c1",
            is_buggy=True,
            defects=[sample_defect],
        )
        pred = make_finding(finding_id="P1", file_path="src/database/query.py", start_line=50, end_line=50)

        result = matcher.evaluate_case(case, [pred])
        assert result.true_positives == 1
        assert result.false_positives == 0
        assert result.false_negatives == 0
        assert len(result.matched_pairs) == 1
        assert result.matched_pairs[0].is_direct_overlap is True

    def test_windows_path_separator_normalization(self, sample_defect):
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)
        case = BenchmarkCase(
            case_id="BUG-001",
            repository="owner/repo",
            commit_hash="c1",
            is_buggy=True,
            defects=[sample_defect],
        )
        # Windows backslashes in prediction
        pred = make_finding(finding_id="P1", file_path="src\\database\\query.py", start_line=50, end_line=50)

        result = matcher.evaluate_case(case, [pred])
        assert result.true_positives == 1
        assert result.false_positives == 0

    def test_acceptable_alternative_cwe_matches(self, sample_defect):
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)
        case = BenchmarkCase(
            case_id="BUG-001",
            repository="owner/repo",
            commit_hash="c1",
            is_buggy=True,
            defects=[sample_defect],
        )
        # Pred emits pre-declared alternative CWE-20 instead of primary CWE-89
        pred = make_finding(finding_id="P1", primary_cwe="CWE-20", category_id=2)

        result = matcher.evaluate_case(case, [pred])
        assert result.true_positives == 1
        assert result.false_positives == 0
        assert result.matched_pairs[0].matched_cwe == "CWE-20"

    def test_incompatible_cwe_fails_match(self, sample_defect):
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)
        case = BenchmarkCase(
            case_id="BUG-001",
            repository="owner/repo",
            commit_hash="c1",
            is_buggy=True,
            defects=[sample_defect],
        )
        # Pred emits CWE-79 (XSS), not in primary or alternative set
        pred = make_finding(finding_id="P1", primary_cwe="CWE-79", category_id=2)

        result = matcher.evaluate_case(case, [pred])
        assert result.true_positives == 0
        assert result.false_positives == 1  # Unmatched prediction = FP
        assert result.false_negatives == 1  # Unmatched GT defect = FN

    def test_boundary_line_at_plus_10_accepted_and_plus_11_rejected(self, sample_defect):
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)
        case = BenchmarkCase(
            case_id="BUG-001",
            repository="owner/repo",
            commit_hash="c1",
            is_buggy=True,
            defects=[sample_defect],
        )

        # Distance +10: line 60 -> Accepted
        pred_10 = make_finding(finding_id="P_10", start_line=60, end_line=60)
        res_10 = matcher.evaluate_case(case, [pred_10])
        assert res_10.true_positives == 1
        assert res_10.false_positives == 0

        # Distance +11: line 61 -> Rejected
        pred_11 = make_finding(finding_id="P_11", start_line=61, end_line=61)
        res_11 = matcher.evaluate_case(case, [pred_11])
        assert res_11.true_positives == 0
        assert res_11.false_positives == 1
        assert res_11.false_negatives == 1

    def test_missing_line_coordinates_produce_fp(self, sample_defect):
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)
        case = BenchmarkCase(
            case_id="BUG-001",
            repository="owner/repo",
            commit_hash="c1",
            is_buggy=True,
            defects=[sample_defect],
        )
        pred_no_lines = make_finding(finding_id="P_NONE", start_line=None, end_line=None)

        result = matcher.evaluate_case(case, [pred_no_lines])
        assert result.true_positives == 0
        assert result.false_positives == 1
        assert result.false_negatives == 1

    def test_one_to_one_consumption_multiple_predictions_one_gt(self, sample_defect):
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)
        case = BenchmarkCase(
            case_id="BUG-001",
            repository="owner/repo",
            commit_hash="c1",
            is_buggy=True,
            defects=[sample_defect],
        )
        # Two valid predictions for the single GT defect
        p1 = make_finding(finding_id="P1", start_line=50, end_line=50)
        p2 = make_finding(finding_id="P2", start_line=52, end_line=52)

        result = matcher.evaluate_case(case, [p1, p2])
        # Exactly 1 consumed as TP, the extra prediction counts as FP!
        assert result.true_positives == 1
        assert result.false_positives == 1
        assert result.false_negatives == 0

    def test_clean_pr_all_predictions_are_false_positives(self):
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)
        clean_case = BenchmarkCase(
            case_id="CLEAN-001",
            repository="owner/repo",
            commit_hash="c_clean",
            is_buggy=False,
            defects=[],
        )
        p1 = make_finding(finding_id="P1", start_line=10, end_line=10)
        p2 = make_finding(finding_id="P2", start_line=20, end_line=20)

        result = matcher.evaluate_case(clean_case, [p1, p2])
        assert result.true_positives == 0
        assert result.false_positives == 2
        assert result.false_negatives == 0

    def test_order_independence_and_shuffled_determinism(self, sample_defect):
        """Shuffle prediction arrays 20 times and verify identical matching output every time."""
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)
        d2 = GroundTruthDefect(
            defect_id="DEF-002",
            category_id=3,
            primary_cwe="CWE-89",
            file_path="src/database/query.py",
            start_line=100,
            end_line=105,
        )
        case = BenchmarkCase(
            case_id="BUG-002",
            repository="owner/repo",
            commit_hash="c2",
            is_buggy=True,
            defects=[sample_defect, d2],
        )

        p1 = make_finding(finding_id="P1", start_line=50, end_line=50)
        p2 = make_finding(finding_id="P2", start_line=102, end_line=102)
        p3 = make_finding(finding_id="P3_EXTRA", start_line=10, end_line=10)

        preds = [p1, p2, p3]
        base_result = matcher.evaluate_case(case, preds)

        for _ in range(20):
            shuffled = list(preds)
            random.shuffle(shuffled)
            res = matcher.evaluate_case(case, shuffled)
            assert res.true_positives == base_result.true_positives
            assert res.false_positives == base_result.false_positives
            assert res.false_negatives == base_result.false_negatives
            assert len(res.matched_pairs) == len(base_result.matched_pairs)

    def test_batch_evaluation_and_metric_formulas(self, sample_defect):
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)
        case_buggy = BenchmarkCase(
            case_id="BUG-001",
            repository="owner/repo",
            commit_hash="c1",
            is_buggy=True,
            defects=[sample_defect],
        )
        case_clean = BenchmarkCase(
            case_id="CLEAN-001",
            repository="owner/repo",
            commit_hash="c2",
            is_buggy=False,
            defects=[],
        )

        # Buggy case: 1 TP, 1 extra FP
        preds_buggy = [
            make_finding(finding_id="P1", start_line=50, end_line=50),
            make_finding(finding_id="P_EXTRA", start_line=200, end_line=200),
        ]
        # Clean case: 1 FP
        preds_clean = [
            make_finding(finding_id="P_CLEAN", start_line=15, end_line=15),
        ]

        metrics, results = matcher.evaluate_batch(
            cases=[case_buggy, case_clean],
            predictions_by_case={
                "BUG-001": preds_buggy,
                "CLEAN-001": preds_clean,
            },
        )

        # TP = 1, FP = 1 (buggy) + 1 (clean) = 2, FN = 0
        assert metrics.true_positives == 1
        assert metrics.false_positives == 2
        assert metrics.false_negatives == 0
        # Precision = 1 / (1 + 2) = 0.3333
        assert metrics.precision == 0.3333
        # Recall = 1 / (1 + 0) = 1.0
        assert metrics.recall == 1.0
        # F1 = 2 * (0.3333 * 1.0) / (1.3333) = 0.5
        assert metrics.f1_score == 0.5
        # FPR: 1 clean case evaluated, 1 flagged -> 1.0
        assert metrics.clean_cases_evaluated == 1
        assert metrics.clean_cases_flagged == 1
        assert metrics.false_positive_rate == 1.0


class TestFalsePositiveRateAndUndefinedMetrics:
    """Tests for FPR (dataset_design_test_case_list.md Section 14, line 416) and explicit undefined metrics."""

    def test_fpr_clean_prs_flagged_over_total_clean_prs(self):
        matcher = OfflineEvaluationMatcher()
        # Create 10 clean PR cases
        clean_cases = [
            BenchmarkCase(
                case_id=f"CLEAN-{i:03d}",
                repository="owner/repo",
                commit_hash=f"sha_{i}",
                is_buggy=False,
                defects=[],
            )
            for i in range(10)
        ]

        # Flag 3 of the 10 clean cases with false positives
        preds_by_case = {
            "CLEAN-001": [make_finding(finding_id="FP-1", start_line=10, end_line=10)],
            "CLEAN-004": [make_finding(finding_id="FP-2", start_line=20, end_line=20)],
            "CLEAN-008": [make_finding(finding_id="FP-3", start_line=30, end_line=30)],
        }

        metrics, _ = matcher.evaluate_batch(clean_cases, preds_by_case)

        # Total clean: 10, flagged: 3 -> FPR = 3 / 10 = 0.3
        assert metrics.clean_cases_evaluated == 10
        assert metrics.clean_cases_flagged == 3
        assert metrics.false_positive_rate == 0.3
        # No GT defects exist in this batch -> Recall is undefined (None)
        assert metrics.recall is None
        # Predictions exist (3 FPs, 0 TP) -> Precision = 0 / 3 = 0.0
        assert metrics.precision == 0.0
        # F1 is undefined (None) when Recall is None
        assert metrics.f1_score is None

    def test_fpr_zero_when_no_clean_prs_flagged(self):
        matcher = OfflineEvaluationMatcher()
        clean_cases = [
            BenchmarkCase(
                case_id=f"CLEAN-{i:03d}",
                repository="owner/repo",
                commit_hash=f"sha_{i}",
                is_buggy=False,
                defects=[],
            )
            for i in range(5)
        ]

        # No predictions on any clean case
        metrics, _ = matcher.evaluate_batch(clean_cases, {})

        assert metrics.clean_cases_evaluated == 5
        assert metrics.clean_cases_flagged == 0
        assert metrics.false_positive_rate == 0.0
        # Zero predictions -> Precision is undefined (None)
        assert metrics.precision is None
        # Zero defects -> Recall is undefined (None)
        assert metrics.recall is None
        assert metrics.f1_score is None

    def test_fpr_one_when_all_clean_prs_flagged(self):
        matcher = OfflineEvaluationMatcher()
        clean_cases = [
            BenchmarkCase(
                case_id=f"CLEAN-{i:03d}",
                repository="owner/repo",
                commit_hash=f"sha_{i}",
                is_buggy=False,
                defects=[],
            )
            for i in range(4)
        ]

        preds_by_case = {
            f"CLEAN-{i:03d}": [make_finding(finding_id=f"FP-{i}", start_line=10, end_line=10)] for i in range(4)
        }

        metrics, _ = matcher.evaluate_batch(clean_cases, preds_by_case)

        assert metrics.clean_cases_evaluated == 4
        assert metrics.clean_cases_flagged == 4
        assert metrics.false_positive_rate == 1.0

    def test_undefined_metrics_when_denominators_are_zero(self):
        """Mathematical undefined values MUST be represented explicitly as None."""
        matcher = OfflineEvaluationMatcher()

        # Batch with ONLY a buggy PR and zero predictions emitted
        d = GroundTruthDefect(
            defect_id="DEF-001",
            category_id=2,
            primary_cwe="CWE-20",
            file_path="src/app.py",
            start_line=10,
            end_line=15,
        )
        case_buggy = BenchmarkCase(
            case_id="BUG-001",
            repository="owner/repo",
            commit_hash="sha_b",
            is_buggy=True,
            defects=[d],
        )

        metrics, _ = matcher.evaluate_batch([case_buggy], {})

        # 0 clean cases -> FPR denominator is zero -> None
        assert metrics.clean_cases_evaluated == 0
        assert metrics.false_positive_rate is None

        # 0 predictions (0 TP, 0 FP) -> Precision denominator is zero -> None
        assert metrics.total_predictions == 0
        assert metrics.precision is None

        # 1 GT defect, 0 matched -> Recall = 0 / 1 = 0.0
        assert metrics.recall == 0.0

        # F1 is None when Precision is None
        assert metrics.f1_score is None

    def test_f1_score_none_when_both_precision_and_recall_are_zero(self):
        """F1 denominator is (Precision + Recall). When both are 0.0, F1 is None."""
        metrics = EvaluationMetrics.calculate(
            tp=0,
            fp=5,
            fn=5,
            clean_cases=0,
            clean_cases_flagged=0,
            buggy_cases=1,
            total_predictions=5,
            total_gt_defects=5,
        )
        assert metrics.precision == 0.0
        assert metrics.recall == 0.0
        assert metrics.f1_score is None


class TestMaximumCardinalityBipartiteRegression:
    """Adversarial regression test: evaluation matcher must not lose valid matches due to greedy order."""

    def test_maximum_cardinality_reassignment_solves_greedy_trap(self):
        """Adversarial scenario:
        - Defect G1: line 50.
        - Defect G2: line 70.
        - Prediction P1: lines 45–75 (spans both G1 and G2; validly matches either).
        - Prediction P2: lines 48–52 (overlaps G1 line 50; CANNOT match G2 line 70).

        A naive greedy algorithm that matches P1 to G1 first leaves P2 unable to match G2,
        yielding only 1 TP, 1 FP, and 1 FN.

        Maximum-cardinality bipartite matching (Kuhn's augmenting path) MUST find the
        assignment P1 -> G2 and P2 -> G1, producing exactly 2 TPs, 0 FPs, and 0 FNs.
        """
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)

        g1 = GroundTruthDefect(
            defect_id="G1",
            category_id=2,
            primary_cwe="CWE-20",
            file_path="src/app.py",
            start_line=50,
            end_line=50,
            description="Defect 1 at line 50",
        )
        g2 = GroundTruthDefect(
            defect_id="G2",
            category_id=2,
            primary_cwe="CWE-20",
            file_path="src/app.py",
            start_line=70,
            end_line=70,
            description="Defect 2 at line 70",
        )

        case = BenchmarkCase(
            case_id="BUG-ADVERSARIAL-001",
            repository="owner/repo",
            commit_hash="sha_adv",
            is_buggy=True,
            defects=[g1, g2],
        )

        p1 = make_finding(
            finding_id="P1",
            file_path="src/app.py",
            start_line=45,
            end_line=75,
            primary_cwe="CWE-20",
            category_id=2,
        )
        p2 = make_finding(
            finding_id="P2",
            file_path="src/app.py",
            start_line=48,
            end_line=52,
            primary_cwe="CWE-20",
            category_id=2,
        )

        # 1. Verify candidate match conditions individually
        can_p1_g1, _ = matcher.is_candidate_match(p1, g1)
        can_p1_g2, _ = matcher.is_candidate_match(p1, g2)
        can_p2_g1, _ = matcher.is_candidate_match(p2, g1)
        can_p2_g2, _ = matcher.is_candidate_match(p2, g2)

        assert can_p1_g1 is True, "P1 must validly match G1"
        assert can_p1_g2 is True, "P1 must validly match G2"
        assert can_p2_g1 is True, "P2 must validly match G1"
        assert can_p2_g2 is False, "P2 must NOT match G2 (distance > 10 lines)"

        # 2. Evaluate with P1 first, then P2
        result_order_1 = matcher.evaluate_case(case, [p1, p2])
        assert result_order_1.true_positives == 2, "Must achieve maximum cardinality 2 TPs"
        assert result_order_1.false_positives == 0, "Zero False Positives expected"
        assert result_order_1.false_negatives == 0, "Zero False Negatives expected"

        # Check exact pair assignments: P1 -> G2, P2 -> G1
        pair_map = {pair.finding_id: pair.defect_id for pair in result_order_1.matched_pairs}
        assert pair_map == {"P1": "G2", "P2": "G1"}

        # 3. Verify stability under reverse prediction ordering [P2, P1]
        result_order_2 = matcher.evaluate_case(case, [p2, p1])
        assert result_order_2.true_positives == 2
        assert result_order_2.false_positives == 0
        assert result_order_2.false_negatives == 0
        pair_map_2 = {pair.finding_id: pair.defect_id for pair in result_order_2.matched_pairs}
        assert pair_map_2 == {"P1": "G2", "P2": "G1"}


class TestCand0032OverlappingToleranceWindows:
    """Regression test suite for CAND-0032 (Zulip BOLA) overlapping location tolerance windows.

    CAND-0032 defines two distinct ground-truth loci in zerver/lib/message.py:
      - G1: lines 825–827 (has_user_message early return bypass)
        Tolerance window [825 - 10, 827 + 10] = [815, 837]
      - G2: lines 842–856 (missing subscription check in has_message_access)
        Tolerance window [842 - 10, 856 + 10] = [832, 866]

    Lines 832–837 fall strictly within BOTH tolerance windows.
    These tests verify that maximum-cardinality bipartite matching strictly enforces 1-to-1
    mapping and prevents a single prediction from double-claiming both defect loci.
    """

    @pytest.fixture
    def cand0032_case(self) -> BenchmarkCase:
        g1 = GroundTruthDefect(
            defect_id="CAND-0032-DEF-1",
            category_id=6,
            primary_cwe="CWE-863",
            acceptable_alternative_cwes={"CWE-285", "CWE-639"},
            file_path="zerver/lib/message.py",
            start_line=825,
            end_line=827,
            description="Blanket user_message check grants unsubscribed access",
        )
        g2 = GroundTruthDefect(
            defect_id="CAND-0032-DEF-2",
            category_id=6,
            primary_cwe="CWE-863",
            acceptable_alternative_cwes={"CWE-285", "CWE-639"},
            file_path="zerver/lib/message.py",
            start_line=842,
            end_line=856,
            description="Missing is_subscribed check for private stream history",
        )
        return BenchmarkCase(
            case_id="CAND-0032",
            repository="zulip/zulip",
            commit_hash="ea0b8cc01133c79033868efee3edc6c1e3fa0f2b",
            is_buggy=True,
            category_id=6,
            defects=[g1, g2],
        )

    def test_single_prediction_in_overlapping_region_cannot_double_claim(self, cand0032_case: BenchmarkCase):
        """A single prediction at line 835 (within tolerance of both G1 and G2) must produce at most 1 TP."""
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)
        p_overlap = make_finding(
            finding_id="PRED-835",
            file_path="zerver/lib/message.py",
            start_line=835,
            end_line=835,
            primary_cwe="CWE-863",
            category_id=6,
        )

        g1, g2 = cand0032_case.defects
        # Verify line 835 is indeed a candidate match for BOTH defects individually
        can_match_g1, direct_g1 = matcher.is_candidate_match(p_overlap, g1)
        can_match_g2, direct_g2 = matcher.is_candidate_match(p_overlap, g2)
        assert can_match_g1 is True, "Line 835 must fall in G1 window [815, 837]"
        assert direct_g1 is False
        assert can_match_g2 is True, "Line 835 must fall in G2 window [832, 866]"
        assert direct_g2 is False

        # Evaluate case: must match exactly 1 defect (1 TP), leaving the other as FN (1 FN, 0 FP)
        metrics = matcher.evaluate_case(cand0032_case, [p_overlap])
        assert metrics.true_positives == 1, "Single prediction must not match both defects!"
        assert metrics.false_positives == 0, "Matched prediction is a TP, not FP"
        assert metrics.false_negatives == 1, "Unmatched defect must be recorded as False Negative"
        assert len(metrics.matched_pairs) == 1

    def test_two_predictions_resolve_both_defects_optimally(self, cand0032_case: BenchmarkCase):
        """Two predictions (one in overlap window line 835, one in G2 core line 850) achieve 2 TPs."""
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)
        p1 = make_finding(
            finding_id="PRED-835",
            file_path="zerver/lib/message.py",
            start_line=835,
            end_line=835,
            primary_cwe="CWE-863",
            category_id=6,
        )
        p2 = make_finding(
            finding_id="PRED-850",
            file_path="zerver/lib/message.py",
            start_line=850,
            end_line=850,
            primary_cwe="CWE-863",
            category_id=6,
        )

        metrics = matcher.evaluate_case(cand0032_case, [p1, p2])
        assert metrics.true_positives == 2
        assert metrics.false_positives == 0
        assert metrics.false_negatives == 0

        # Maximum cardinality bipartite matching routes P1 to G1 (since P2 can only match G2)
        pair_map = {pair.finding_id: pair.defect_id for pair in metrics.matched_pairs}
        assert pair_map == {"PRED-835": "CAND-0032-DEF-1", "PRED-850": "CAND-0032-DEF-2"}

    def test_adversarial_order_augmenting_path_reassignment(self, cand0032_case: BenchmarkCase):
        """Adversarial prediction arrangement proving Kuhn's augmenting path reassigns P1 -> G2 so P2 -> G1.

        Arrangement:
          - G1: [825, 827], tolerance [815, 837]
          - G2: [842, 856], tolerance [832, 866]
          - P1 (PRED-835): line 835 falls in overlap [832, 837], so it can match G1 or G2.
          - P2 (PRED-820): line 820 falls in [815, 837] (G1 only), but NOT in G2 [832, 866].

        When predictions are presented in order [P1, P2]:
          - A greedy matcher would process P1 first, pairing P1 -> G1 (defect 1).
          - Next, P2 can only match G1, but G1 is already occupied by P1.
          - A greedy approach without augmenting paths would fail to pair P2, yielding only 1 TP (and 1 FP, 1 FN).
          - Kuhn's augmenting path algorithm discovers that P1 can be alternate-routed to G2, freeing G1
            for P2, achieving maximum cardinality 2 TPs (0 FP, 0 FN).
        """
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)
        p1 = make_finding(
            finding_id="PRED-835",
            file_path="zerver/lib/message.py",
            start_line=835,
            end_line=835,
            primary_cwe="CWE-863",
            category_id=6,
        )
        p2 = make_finding(
            finding_id="PRED-820",
            file_path="zerver/lib/message.py",
            start_line=820,
            end_line=820,
            primary_cwe="CWE-863",
            category_id=6,
        )

        g1, g2 = cand0032_case.defects
        # Verify candidate match topology:
        # P1 can match G1 or G2
        can_p1_g1, _ = matcher.is_candidate_match(p1, g1)
        can_p1_g2, _ = matcher.is_candidate_match(p1, g2)
        assert can_p1_g1 is True, "P1 (line 835) must be valid candidate match for G1"
        assert can_p1_g2 is True, "P1 (line 835) must be valid candidate match for G2"

        # P2 can match ONLY G1
        can_p2_g1, _ = matcher.is_candidate_match(p2, g1)
        can_p2_g2, _ = matcher.is_candidate_match(p2, g2)
        assert can_p2_g1 is True, "P2 (line 820) must be valid candidate match for G1"
        assert can_p2_g2 is False, "P2 (line 820) must NOT match G2 (distance > 10 lines)"

        # 1. Adversarial order [P1, P2]: P1 arrives first and could greedily take G1
        metrics_forward = matcher.evaluate_case(cand0032_case, [p1, p2])
        assert metrics_forward.true_positives == 2, (
            "Kuhn augmenting path must reassign P1 -> G2 so P2 -> G1 achieves 2 TPs"
        )
        assert metrics_forward.false_positives == 0, "No false positives expected"
        assert metrics_forward.false_negatives == 0, "No false negatives expected"

        pair_map_forward = {pair.finding_id: pair.defect_id for pair in metrics_forward.matched_pairs}
        assert pair_map_forward == {"PRED-835": "CAND-0032-DEF-2", "PRED-820": "CAND-0032-DEF-1"}

        # 2. Reverse order [P2, P1]: verify order invariance
        metrics_reverse = matcher.evaluate_case(cand0032_case, [p2, p1])
        assert metrics_reverse.true_positives == 2
        assert metrics_reverse.false_positives == 0
        assert metrics_reverse.false_negatives == 0
        pair_map_reverse = {pair.finding_id: pair.defect_id for pair in metrics_reverse.matched_pairs}
        assert pair_map_reverse == {"PRED-835": "CAND-0032-DEF-2", "PRED-820": "CAND-0032-DEF-1"}

    def test_extra_prediction_in_overlapping_window_becomes_false_positive(self, cand0032_case: BenchmarkCase):
        """Three predictions for 2 defects result in 2 TPs and 1 FP, preventing surplus inflation."""
        matcher = OfflineEvaluationMatcher(tolerance_lines=10)
        p1 = make_finding(
            finding_id="PRED-826",
            file_path="zerver/lib/message.py",
            start_line=826,
            end_line=826,
            primary_cwe="CWE-863",
            category_id=6,
        )
        p2 = make_finding(
            finding_id="PRED-835",
            file_path="zerver/lib/message.py",
            start_line=835,
            end_line=835,
            primary_cwe="CWE-863",
            category_id=6,
        )
        p3 = make_finding(
            finding_id="PRED-850",
            file_path="zerver/lib/message.py",
            start_line=850,
            end_line=850,
            primary_cwe="CWE-863",
            category_id=6,
        )

        metrics = matcher.evaluate_case(cand0032_case, [p1, p2, p3])
        assert metrics.true_positives == 2
        assert metrics.false_positives == 1
        assert metrics.false_negatives == 0
