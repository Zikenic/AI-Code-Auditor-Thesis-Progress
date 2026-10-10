"""Unit tests for auditor domain models, taxonomy boundaries, and ground-truth invariants."""

import pytest
from pydantic import ValidationError

from auditor.models.finding import (
    DetectionLayer,
    PredictedFinding,
)
from auditor.models.ground_truth import BenchmarkCase, GroundTruthDefect, ImpactType
from auditor.models.taxonomy import (
    ACTIVE_TAXONOMY,
    TaxonomyConfig,
)


class TestTaxonomyAndBounds:
    def test_default_taxonomy_allows_one_to_six(self):
        for cat_id in range(1, 7):
            assert ACTIVE_TAXONOMY.is_approved(cat_id) is True
            assert ACTIVE_TAXONOMY.validate_category(cat_id) == cat_id

    def test_default_taxonomy_rejects_category_seven_and_eight_by_default(self):
        for cat_id in [7, 8, 9, 0, -1]:
            assert ACTIVE_TAXONOMY.is_approved(cat_id) is False
            with pytest.raises(ValueError, match="not in the active approved taxonomy"):
                ACTIVE_TAXONOMY.validate_category(cat_id)

    def test_taxonomy_config_can_approve_category_seven_and_eight(self):
        custom_config = TaxonomyConfig(approved_category_ids={1, 2, 3, 4, 5, 6, 7, 8})
        assert custom_config.is_approved(7) is True
        assert custom_config.is_approved(8) is True
        assert custom_config.validate_category(7) == 7
        assert custom_config.validate_category(8) == 8

    def test_taxonomy_config_rejects_exceeding_max_permissible_cap(self):
        with pytest.raises(ValueError, match="exceeds permissible taxonomy bounds"):
            TaxonomyConfig(approved_category_ids={1, 2, 3, 4, 5, 6, 7, 8, 9})

    def test_taxonomy_config_rejects_empty_set(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            TaxonomyConfig(approved_category_ids=set())


class TestCategory1ImpactInvariant:
    def test_category_1_defect_requires_impact_functional_or_security(self):
        # Valid functional impact
        defect_func = GroundTruthDefect(
            defect_id="DEF-001",
            category_id=1,
            impact=ImpactType.FUNCTIONAL,
            primary_cwe="CWE-193",
            file_path="src/module.py",
            start_line=10,
            end_line=12,
        )
        assert defect_func.impact == ImpactType.FUNCTIONAL

        # Valid security impact
        defect_sec = GroundTruthDefect(
            defect_id="DEF-002",
            category_id=1,
            impact=ImpactType.SECURITY,
            primary_cwe="CWE-193",
            file_path="src/module.py",
            start_line=10,
            end_line=12,
        )
        assert defect_sec.impact == ImpactType.SECURITY

    def test_category_1_defect_rejects_none_impact(self):
        with pytest.raises(ValidationError, match="Category 1 defects MUST explicitly declare impact"):
            GroundTruthDefect(
                defect_id="DEF-001",
                category_id=1,
                impact=None,
                primary_cwe="CWE-193",
                file_path="src/module.py",
                start_line=10,
                end_line=12,
            )

    def test_category_2_to_6_defect_rejects_non_none_impact(self):
        for cat_id in range(2, 7):
            with pytest.raises(ValidationError, match="must have impact=None"):
                GroundTruthDefect(
                    defect_id=f"DEF-00{cat_id}",
                    category_id=cat_id,
                    impact=ImpactType.SECURITY,
                    primary_cwe="CWE-20",
                    file_path="src/module.py",
                    start_line=10,
                    end_line=12,
                )


class TestImpactMetadataAndTaxonomyGovernance:
    """Comprehensive regression test suite for Prompt 4 taxonomy & impact governance."""

    def test_scenario_1_category_1_valid_impact(self):
        """Category 1 accepts valid 'functional' and 'security' impact values."""
        defect_func = GroundTruthDefect(
            defect_id="DEF-001-F",
            category_id=1,
            impact="functional",
            primary_cwe="CWE-670",
            file_path="src/app.py",
            start_line=10,
            end_line=15,
        )
        assert defect_func.impact == ImpactType.FUNCTIONAL

        defect_sec = GroundTruthDefect(
            defect_id="DEF-001-S",
            category_id=1,
            impact="security",
            primary_cwe="CWE-670",
            file_path="src/app.py",
            start_line=10,
            end_line=15,
        )
        assert defect_sec.impact == ImpactType.SECURITY

    def test_scenario_2_category_1_missing_impact_rejected(self):
        """Category 1 rejects missing/None impact."""
        with pytest.raises(ValidationError, match="Category 1 defects MUST explicitly declare impact"):
            GroundTruthDefect(
                defect_id="DEF-001-NONE",
                category_id=1,
                impact=None,
                primary_cwe="CWE-670",
                file_path="src/app.py",
                start_line=10,
                end_line=15,
            )

    def test_scenario_3_category_1_invalid_impact_rejected(self):
        """Category 1 rejects unrecognized impact values (e.g. 'critical', 'low')."""
        for invalid in ["critical", "low", "high", "moderate", "none"]:
            with pytest.raises(ValidationError, match="Input should be 'functional' or 'security'"):
                GroundTruthDefect(
                    defect_id=f"DEF-001-{invalid}",
                    category_id=1,
                    impact=invalid,
                    primary_cwe="CWE-670",
                    file_path="src/app.py",
                    start_line=10,
                    end_line=15,
                )

    def test_scenario_4_categories_2_to_6_valid_without_impact(self):
        """Categories 2 through 6 are valid when impact is None."""
        for cat_id in range(2, 7):
            defect = GroundTruthDefect(
                defect_id=f"DEF-CAT{cat_id}",
                category_id=cat_id,
                impact=None,
                primary_cwe="CWE-20",
                file_path="src/app.py",
                start_line=20,
                end_line=25,
            )
            assert defect.impact is None
            assert defect.category_id == cat_id

    def test_scenario_5_categories_2_to_6_reject_all_impact_values(self):
        """Categories 2 through 6 strictly reject 'security' and 'functional' impact values."""
        for cat_id in range(2, 7):
            for bad_impact in [ImpactType.SECURITY, ImpactType.FUNCTIONAL, "security", "functional"]:
                with pytest.raises(ValidationError, match="must have impact=None"):
                    GroundTruthDefect(
                        defect_id=f"DEF-CAT{cat_id}-BAD",
                        category_id=cat_id,
                        impact=bad_impact,
                        primary_cwe="CWE-20",
                        file_path="src/app.py",
                        start_line=20,
                        end_line=25,
                    )

    def test_scenario_6_categories_7_and_8_governance(self):
        """Categories 7 and 8 are rejected by default taxonomy; allowed only when explicitly configured."""
        # Default taxonomy rejects categories 7 and 8
        for cat_id in [7, 8]:
            assert ACTIVE_TAXONOMY.is_approved(cat_id) is False
            with pytest.raises(ValidationError, match="not in the active approved taxonomy"):
                GroundTruthDefect(
                    defect_id=f"DEF-CAT{cat_id}",
                    category_id=cat_id,
                    impact=None,
                    primary_cwe="CWE-20",
                    file_path="src/app.py",
                    start_line=20,
                    end_line=25,
                )

        # Extended taxonomy allows categories 7 and 8
        extended_config = TaxonomyConfig(approved_category_ids={1, 2, 3, 4, 5, 6, 7, 8})
        assert extended_config.is_approved(7) is True
        assert extended_config.is_approved(8) is True
        assert extended_config.validate_category(7) == 7
        assert extended_config.validate_category(8) == 8


class TestCwePolicyAndGroundTruth:
    def test_cwe_normalization(self):
        defect = GroundTruthDefect(
            defect_id="DEF-001",
            category_id=3,
            primary_cwe="89",
            acceptable_alternative_cwes={"cwe-20", "SQLI"},
            file_path="src/db.py",
            start_line=50,
            end_line=55,
        )
        assert defect.primary_cwe == "CWE-89"
        assert "CWE-20" in defect.acceptable_alternative_cwes
        assert "SQLI" in defect.acceptable_alternative_cwes

    def test_cwe_alternatives_cap_at_two(self):
        with pytest.raises(ValidationError, match="limits pre-declared alternative CWEs to at most 2"):
            GroundTruthDefect(
                defect_id="DEF-001",
                category_id=3,
                primary_cwe="CWE-89",
                acceptable_alternative_cwes={"CWE-20", "CWE-94", "CWE-74"},
                file_path="src/db.py",
                start_line=50,
                end_line=55,
            )

    def test_defect_line_range_ordering(self):
        with pytest.raises(ValidationError, match="cannot be less than start_line"):
            GroundTruthDefect(
                defect_id="DEF-001",
                category_id=2,
                primary_cwe="CWE-20",
                file_path="src/app.py",
                start_line=50,
                end_line=40,
            )

    def test_cwe_match_helper(self):
        defect = GroundTruthDefect(
            defect_id="DEF-001",
            category_id=3,
            primary_cwe="CWE-89",
            acceptable_alternative_cwes={"CWE-20"},
            file_path="src/db.py",
            start_line=50,
            end_line=55,
        )
        assert defect.matches_cwe("CWE-89") is True
        assert defect.matches_cwe("89") is True
        assert defect.matches_cwe("CWE-20") is True
        assert defect.matches_cwe("20") is True
        assert defect.matches_cwe("CWE-79") is False


class TestBenchmarkCaseConsistency:
    def test_clean_case_cannot_have_defects(self):
        defect = GroundTruthDefect(
            defect_id="DEF-001",
            category_id=2,
            primary_cwe="CWE-20",
            file_path="src/app.py",
            start_line=10,
            end_line=15,
        )
        with pytest.raises(ValidationError, match="Clean case .* cannot contain ground-truth defects"):
            BenchmarkCase(
                case_id="CLEAN-01",
                repository="owner/repo",
                commit_hash="abc1234",
                is_buggy=False,
                defects=[defect],
            )

    def test_buggy_case_must_have_at_least_one_defect(self):
        with pytest.raises(ValidationError, match="must declare at least one ground-truth defect"):
            BenchmarkCase(
                case_id="BUG-01",
                repository="owner/repo",
                commit_hash="abc1234",
                is_buggy=True,
                defects=[],
            )


class TestPredictedFindingModel:
    def test_finding_defaults_end_line_to_start_line(self):
        finding = PredictedFinding(
            finding_id="FIND-01",
            detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
            tool_name="ruff",
            category_id=2,
            primary_cwe="CWE-20",
            file_path="src/app.py",
            start_line=25,
            title="Unvalidated input",
            description="Detail message",
        )
        assert finding.start_line == 25
        assert finding.end_line == 25
        assert finding.has_line_coordinates() is True

    def test_finding_without_line_coordinates(self):
        finding = PredictedFinding(
            finding_id="FIND-02",
            detection_layer=DetectionLayer.HEURISTIC_LLM,
            tool_name="gemini-1.5-pro",
            category_id=2,
            primary_cwe="CWE-20",
            file_path="src/app.py",
            start_line=None,
            end_line=None,
            title="File-level smell",
            description="No line numbers",
        )
        assert finding.has_line_coordinates() is False
