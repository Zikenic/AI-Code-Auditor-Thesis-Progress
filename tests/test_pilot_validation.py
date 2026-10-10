"""Reproducible test suite validating the 12 Ground-Truth-Verified pilot cases.

Enforces strict parity against independently verified ground-truth records:
- Hard-coded expected defect counts and ground-truth loci.
- Rejection of duplicate or subsumed incidental line numbers.
- Category 1 impact exclusivity and Category 2..6 impact=None enforcement.
"""

import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from auditor.dataset import (
    get_default_pilot_data_path,
    load_pilot_benchmark_cases,
    load_pilot_cases_from_json,
    parse_case_dict_to_benchmark_case,
)
from auditor.models.ground_truth import BenchmarkCase, ImpactType, ReproducerStatus
from tools.compute_census import compute_census
from tools.import_pilot_markdown import parse_ground_truth_locus

CANONICAL_JSON_PATH = Path("data/pilot_cases.json")

# Authoritative regression fixture derived from verified ground-truth records
VERIFIED_PILOT_FIXTURE: dict[str, dict[str, Any]] = {
    "CAND-0001": {
        "category_id": 1,
        "impact": ImpactType.FUNCTIONAL,
        "repository": "tornadoweb/tornado",
        "commit_hash": "2ca8821d006f6693f920a4b183a3a7c985a5c8ad",
        "target_file": "tornado/http1connection.py",
        "primary_cwe": "CWE-670",
        "acceptable_alternative_cwes": {"CWE-20", "CWE-440"},
        "expected_defect_count": 1,
        "expected_line_ranges": [(390, 394)],
    },
    "CAND-0002": {
        "category_id": 1,
        "impact": ImpactType.FUNCTIONAL,
        "repository": "tiangolo/fastapi",
        "commit_hash": "210af1fd3dc0f612a08fa02a0cb3f5adb81e5bfb",
        "target_file": "fastapi/routing.py",
        "primary_cwe": "CWE-670",
        "acceptable_alternative_cwes": {"CWE-440"},
        "expected_defect_count": 1,
        "expected_line_ranges": [(498, 502)],
    },
    "CAND-0007": {
        "category_id": 2,
        "impact": None,
        "repository": "tiangolo/fastapi",
        "commit_hash": "90120dd6e83d997fa2f7f54119a2e0cf906b1ded",
        "target_file": "fastapi/routing.py",
        "primary_cwe": "CWE-352",
        "acceptable_alternative_cwes": {"CWE-20", "CWE-345"},
        "expected_defect_count": 1,
        "expected_line_ranges": [(182, 184)],
    },
    "CAND-0009": {
        "category_id": 2,
        "impact": None,
        "repository": "pallets/jinja",
        "commit_hash": "a7863ba9d3521f1450f821119c50d19d7ecea329",
        "target_file": "src/jinja2/filters.py",
        "primary_cwe": "CWE-79",
        "acceptable_alternative_cwes": {"CWE-20", "CWE-116"},
        "expected_defect_count": 2,
        "expected_line_ranges": [(250, 250), (292, 293)],
    },
    "CAND-0014": {
        "category_id": 3,
        "impact": None,
        "repository": "django/django",
        "commit_hash": "425718726b7d2edd7b8a043f8976e437262b5098",
        "target_file": "django/db/models/functions/datetime.py",
        "primary_cwe": "CWE-89",
        "acceptable_alternative_cwes": {"CWE-20", "CWE-943"},
        "expected_defect_count": 2,
        "expected_line_ranges": [(45, 51), (225, 236)],
    },
    "CAND-0017": {
        "category_id": 3,
        "impact": None,
        "repository": "tortoise/tortoise-orm",
        "commit_hash": "816ff00e988f79b4ff1601f247062bb5eb9db802",
        "target_file": "tortoise/backends/mysql/executor.py",
        "primary_cwe": "CWE-89",
        "acceptable_alternative_cwes": {"CWE-20", "CWE-943"},
        "expected_defect_count": 1,
        "expected_line_ranges": [(19, 45)],
    },
    "CAND-0019": {
        "category_id": 4,
        "impact": None,
        "repository": "aio-libs/aiohttp",
        "commit_hash": "33ccdfb0a12690af5bb49bda2319ec0907fa7827",
        "target_file": "aiohttp/web_urldispatcher.py",
        "primary_cwe": "CWE-22",
        "acceptable_alternative_cwes": {"CWE-20", "CWE-59"},
        "expected_defect_count": 2,
        "expected_line_ranges": [(643, 645), (574, 576)],
    },
    "CAND-0021": {
        "category_id": 4,
        "impact": None,
        "repository": "encode/starlette",
        "commit_hash": "24c1fac62a80bb153c6548145334fc643991e35a",
        "target_file": "starlette/staticfiles.py",
        "primary_cwe": "CWE-22",
        "acceptable_alternative_cwes": {"CWE-20"},
        "expected_defect_count": 1,
        "expected_line_ranges": [(172, 172)],
    },
    "CAND-0025": {
        "category_id": 5,
        "impact": None,
        "repository": "jpadilla/pyjwt",
        "commit_hash": "24b29adfebcb4f057a3cef5aaf35653bc0c1c8cc",
        "target_file": "jwt/algorithms.py",
        "primary_cwe": "CWE-347",
        "acceptable_alternative_cwes": {"CWE-287", "CWE-327"},
        "expected_defect_count": 1,
        "expected_line_ranges": [(186, 197)],
    },
    "CAND-0027": {
        "category_id": 5,
        "impact": None,
        "repository": "lepture/authlib",
        "commit_hash": "bb7a315befbad333faf9a23ef574d6e3134a6774",
        "target_file": "authlib/jose/__init__.py",
        "primary_cwe": "CWE-347",
        "acceptable_alternative_cwes": {"CWE-287", "CWE-327"},
        "expected_defect_count": 1,
        "expected_line_ranges": [(49, 49)],
    },
    "CAND-0031": {
        "category_id": 6,
        "impact": None,
        "repository": "jupyterhub/jupyterhub",
        "commit_hash": "b4053616743eb011e5bb568700f25afca17aef53",
        "target_file": "jupyterhub/apihandlers/users.py",
        "primary_cwe": "CWE-269",
        "acceptable_alternative_cwes": {"CWE-285", "CWE-863"},
        "expected_defect_count": 2,
        "expected_line_ranges": [(265, 267), (328, 331)],
    },
    "CAND-0032": {
        "category_id": 6,
        "impact": None,
        "repository": "zulip/zulip",
        "commit_hash": "ea0b8cc01133c79033868efee3edc6c1e3fa0f2b",
        "target_file": "zerver/lib/message.py",
        "primary_cwe": "CWE-863",
        "acceptable_alternative_cwes": {"CWE-285", "CWE-639"},
        "expected_defect_count": 2,
        "expected_line_ranges": [(825, 827), (842, 856)],
    },
}

VERIFIED_BATCH1_FIXTURE: dict[str, dict[str, Any]] = {
    "CAND-0006": {
        "category_id": 1,
        "impact": ImpactType.FUNCTIONAL,
        "repository": "scrapy/scrapy",
        "commit_hash": "f02c3d1dcf3e4880388d19e961e7911be5dc54ff",
        "target_file": "scrapy/utils/datatypes.py",
        "primary_cwe": "CWE-476",
        "acceptable_alternative_cwes": {"CWE-670"},
        "expected_defect_count": 1,
        "expected_line_ranges": [(318, 319)],
        "contextual_files": [],
        "verification_status": "GROUND_TRUTH_VERIFIED",
    },
    "CAND-0015": {
        "category_id": 3,
        "impact": None,
        "repository": "django/django",
        "commit_hash": "6b178a3e930f72069f3cda2e6a09d1b320fc09ec",
        "target_file": "django/contrib/postgres/aggregates/general.py",
        "primary_cwe": "CWE-89",
        "acceptable_alternative_cwes": {"CWE-943"},
        "expected_defect_count": 1,
        "expected_line_ranges": [(54, 58)],
        "contextual_files": [],
        "verification_status": "GROUND_TRUTH_VERIFIED",
    },
    "CAND-0020": {
        "category_id": 4,
        "impact": None,
        "repository": "pallets/werkzeug",
        "commit_hash": "50cfeebcb0727e18cc52ffbeb125f4a66551179b",
        "target_file": "src/werkzeug/security.py",
        "primary_cwe": "CWE-22",
        "acceptable_alternative_cwes": {"CWE-20"},
        "expected_defect_count": 1,
        "expected_line_ranges": [(151, 157)],
        "contextual_files": [],
        "verification_status": "GROUND_TRUTH_VERIFIED",
    },
    "CAND-0026": {
        "category_id": 5,
        "impact": None,
        "repository": "paramiko/paramiko",
        "commit_hash": "aefd28a7f00c4250d113d375e96abf5da3eb89f9",
        "target_file": "paramiko/transport.py",
        "primary_cwe": "CWE-287",
        "acceptable_alternative_cwes": {"CWE-305"},
        "expected_defect_count": 1,
        "expected_line_ranges": [(1822, 1828)],
        "contextual_files": ["paramiko/common.py"],
        "verification_status": "GROUND_TRUTH_VERIFIED",
    },
    "CAND-0033": {
        "category_id": 6,
        "impact": None,
        "repository": "zulip/zulip",
        "commit_hash": "b1007916b03a40841ba141f5e4f041aeaeaaa010",
        "target_file": "zerver/actions/typing.py",
        "primary_cwe": "CWE-863",
        "acceptable_alternative_cwes": {"CWE-639"},
        "expected_defect_count": 1,
        "expected_line_ranges": [(83, 85)],
        "contextual_files": [],
        "verification_status": "GROUND_TRUTH_VERIFIED",
    },
    "CAND-0008": {
        "category_id": 2,
        "impact": None,
        "repository": "Kludex/python-multipart",
        "commit_hash": "d3d16dae4b061c34fe9d3c9081d9800c49fc1f7a",
        "target_file": "multipart/multipart.py",
        "primary_cwe": "CWE-1333",
        "acceptable_alternative_cwes": {"CWE-400"},
        "expected_defect_count": 1,
        "expected_line_ranges": [(72, 75)],
        "contextual_files": [],
        "verification_status": "GROUND_TRUTH_VERIFIED",
    },
}

# In Phase 3C, CAND-0003 was replaced by verified CAND-0006; all 18 cases are GROUND_TRUTH_VERIFIED.
PENDING_BATCH1_FIXTURE: dict[str, dict[str, Any]] = {}


@pytest.fixture
def pilot_cases() -> list[BenchmarkCase]:
    return load_pilot_benchmark_cases(CANONICAL_JSON_PATH)


def test_eighteen_ground_truth_cases_loaded_from_canonical_json(pilot_cases):
    """Confirm all 18 cases (12 pilot + 6 Batch 1) are loaded from canonical JSON."""
    assert len(pilot_cases) == 18
    actual_ids = {c.case_id for c in pilot_cases}
    assert set(VERIFIED_PILOT_FIXTURE.keys()).issubset(actual_ids)
    assert set(VERIFIED_BATCH1_FIXTURE.keys()).issubset(actual_ids)
    assert set(PENDING_BATCH1_FIXTURE.keys()).issubset(actual_ids)


def test_loader_only_verified_filter():
    """Confirm only_verified=True loads all 18 verified cases (12 pilot + 6 Batch 1)."""
    verified = load_pilot_benchmark_cases(CANONICAL_JSON_PATH, only_verified=True)
    assert len(verified) == 18
    verified_ids = {c.case_id for c in verified}
    assert verified_ids == set(VERIFIED_PILOT_FIXTURE.keys()) | set(VERIFIED_BATCH1_FIXTURE.keys())
    assert "CAND-0006" in verified_ids
    assert "CAND-0008" in verified_ids


def test_hardcoded_fixture_defect_counts_and_loci(pilot_cases):
    """Assert all cases match expected defects, loci, contextual files, and verification statuses."""
    case_map = {c.case_id: c for c in pilot_cases}

    # 1. Verify 12 pilot cases (17 defects)
    total_pilot_defects = 0
    for case_id, expected in VERIFIED_PILOT_FIXTURE.items():
        case = case_map[case_id]
        assert len(case.defects) == expected["expected_defect_count"], (
            f"Pilot defect count mismatch for {case_id}: expected {expected['expected_defect_count']}, got {len(case.defects)}"
        )
        total_pilot_defects += len(case.defects)

        actual_ranges = [(d.start_line, d.end_line) for d in case.defects]
        assert actual_ranges == expected["expected_line_ranges"], (
            f"Pilot locus mismatch for {case_id}: expected {expected['expected_line_ranges']}, got {actual_ranges}"
        )
        assert case.repository == expected["repository"]
        assert case.commit_hash == expected["commit_hash"]
        assert case.verification_status == "GROUND_TRUTH_VERIFIED"

        for defect in case.defects:
            assert defect.file_path == expected["target_file"]
            assert defect.primary_cwe == expected["primary_cwe"]
            assert defect.acceptable_alternative_cwes == expected["acceptable_alternative_cwes"]
            assert defect.category_id == expected["category_id"]
            assert defect.impact == expected["impact"]

    assert total_pilot_defects == 17

    # 2. Verify 6 verified Batch 1 cases (6 defects)
    total_verified_batch1_defects = 0
    for case_id, expected in VERIFIED_BATCH1_FIXTURE.items():
        case = case_map[case_id]
        assert len(case.defects) == expected["expected_defect_count"], (
            f"Batch 1 defect count mismatch for {case_id}: expected {expected['expected_defect_count']}, got {len(case.defects)}"
        )
        total_verified_batch1_defects += len(case.defects)

        actual_ranges = [(d.start_line, d.end_line) for d in case.defects]
        assert actual_ranges == expected["expected_line_ranges"], (
            f"Batch 1 locus mismatch for {case_id}: expected {expected['expected_line_ranges']}, got {actual_ranges}"
        )
        assert case.repository == expected["repository"]
        assert case.commit_hash == expected["commit_hash"]
        assert case.verification_status == expected["verification_status"]
        assert case.contextual_files == expected["contextual_files"]

        for defect in case.defects:
            assert defect.file_path == expected["target_file"]
            assert defect.primary_cwe == expected["primary_cwe"]
            assert defect.acceptable_alternative_cwes == expected["acceptable_alternative_cwes"]
            assert defect.category_id == expected["category_id"]
            assert defect.impact == expected["impact"]

    assert total_verified_batch1_defects == 6

    # 3. Verify pending Batch 1 cases (0 pending after CAND-0003 replacement)
    total_pending_batch1_defects = 0
    for case_id, expected in PENDING_BATCH1_FIXTURE.items():
        case = case_map[case_id]
        assert len(case.defects) == expected["expected_defect_count"]
        total_pending_batch1_defects += len(case.defects)

        actual_ranges = [(d.start_line, d.end_line) for d in case.defects]
        assert actual_ranges == expected["expected_line_ranges"]
        assert case.repository == expected["repository"]
        assert case.commit_hash == expected["commit_hash"]
        assert case.verification_status == expected["verification_status"]
        assert case.contextual_files == expected["contextual_files"]

        for defect in case.defects:
            assert defect.file_path == expected["target_file"]
            assert defect.primary_cwe == expected["primary_cwe"]
            assert defect.acceptable_alternative_cwes == expected["acceptable_alternative_cwes"]
            assert defect.category_id == expected["category_id"]
            assert defect.impact == expected["impact"]

    assert total_pending_batch1_defects == 0
    assert total_pilot_defects + total_verified_batch1_defects == 23


def test_fixture_fails_if_duplicate_locus_introduced():
    """Regression test: verify that adding a duplicate inner locus fails the fixture check."""
    mutated_ranges = [(390, 394), (393, 393)]
    expected = VERIFIED_PILOT_FIXTURE["CAND-0001"]["expected_line_ranges"]
    assert mutated_ranges != expected
    assert len(mutated_ranges) != VERIFIED_PILOT_FIXTURE["CAND-0001"]["expected_defect_count"]


def test_fixture_fails_if_locus_disappears():
    """Regression test: verify that omitting an expected locus fails the fixture check."""
    mutated_ranges = [(250, 250)]  # Missing (292, 293)
    expected = VERIFIED_PILOT_FIXTURE["CAND-0009"]["expected_line_ranges"]
    assert mutated_ranges != expected


def test_fixture_fails_if_range_boundary_mutated():
    """Regression test: verify that changing boundary line values fails the fixture check."""
    mutated_ranges = [(390, 395)]  # Shifted end line
    expected = VERIFIED_PILOT_FIXTURE["CAND-0001"]["expected_line_ranges"]
    assert mutated_ranges != expected


def test_importer_parser_ignores_incidental_and_subsumed_lines():
    """Directly test that parse_ground_truth_locus strips parenthetical notes and subsumed lines."""
    # Parenthetical note with inner line mention must be ignored
    cand1_locus = 'Lines 390–394 (specifically line 393: `and "Transfer-Encoding" not in headers`)'
    assert parse_ground_truth_locus(cand1_locus) == [[390, 394]]

    cand2_locus = (
        "Lines 498–502 (specifically line 501: `route = APIWebSocketRoute(path, endpoint=endpoint, name=name)`)"
    )
    assert parse_ground_truth_locus(cand2_locus) == [[498, 502]]

    # Disjoint ranges with narrative must both be extracted
    cand9_locus = 'Line 250 (`_space_re = re.compile(r"\\s", flags=re.ASCII)`) and Lines 292–293 (`if _space_re.search(key) is not None: raise ValueError(...)`)'
    assert parse_ground_truth_locus(cand9_locus) == [[250, 250], [292, 293]]

    # Explicit subsumption filter test
    subsumed_test = "Lines 100–200 and Line 150"
    assert parse_ground_truth_locus(subsumed_test) == [[100, 200]]


def test_category_1_impact_metadata(pilot_cases):
    """Category 1 cases (CAND-0001, CAND-0002, CAND-0006) must declare impact=functional."""
    cat1_cases = [c for c in pilot_cases if c.case_id in ("CAND-0001", "CAND-0002", "CAND-0006")]
    assert len(cat1_cases) == 3
    for case in cat1_cases:
        for defect in case.defects:
            assert defect.category_id == 1
            assert defect.impact == ImpactType.FUNCTIONAL


def test_categories_2_to_6_have_none_impact(pilot_cases):
    """Categories 2 through 6 cases must have impact=None across all defects."""
    cat2_to_6_cases = [c for c in pilot_cases if c.case_id not in ("CAND-0001", "CAND-0002", "CAND-0006")]
    assert len(cat2_to_6_cases) == 15
    for case in cat2_to_6_cases:
        for defect in case.defects:
            assert defect.category_id in (2, 3, 4, 5, 6)
            assert defect.impact is None


def test_application_loader_uses_canonical_dataset():
    """Verify that get_default_pilot_data_path resolves to canonical data/pilot_cases.json."""
    default_path = get_default_pilot_data_path()
    assert default_path.name == "pilot_cases.json"
    assert "data" in default_path.parts

    cases = load_pilot_benchmark_cases()
    assert len(cases) == 18
    assert sum(len(c.defects) for c in cases) == 23

    # Verified cases only: all 18 cases verified after Phase 3C replacement
    verified_cases = load_pilot_benchmark_cases(only_verified=True)
    assert len(verified_cases) == 18
    assert sum(len(c.defects) for c in verified_cases) == 23


def test_loader_strictly_enforces_category_2_to_6_impact_none():
    """Verify that the loader does not silently strip invalid impact on Categories 2..6."""
    invalid_dict = {
        "case_id": "CAND-TEST-CAT2",
        "repository": "owner/repo",
        "commit_hash": "a" * 40,
        "is_buggy": True,
        "category_id": 2,
        "impact": "security",  # Invalid for Category 2
        "primary_cwe": "CWE-20",
        "target_file": "src/app.py",
        "line_ranges": [[10, 20]],
    }
    with pytest.raises(ValidationError, match="Category 2 defects must have impact=None"):
        parse_case_dict_to_benchmark_case(invalid_dict)


def test_loader_strictly_enforces_category_1_requires_impact():
    """Verify that the loader does not allow Category 1 defects without impact."""
    invalid_dict = {
        "case_id": "CAND-TEST-CAT1",
        "repository": "owner/repo",
        "commit_hash": "a" * 40,
        "is_buggy": True,
        "category_id": 1,
        "impact": None,  # Invalid for Category 1
        "primary_cwe": "CWE-670",
        "target_file": "src/app.py",
        "line_ranges": [[10, 20]],
    }
    with pytest.raises(ValidationError, match="Category 1 defects MUST explicitly declare impact"):
        parse_case_dict_to_benchmark_case(invalid_dict)


def test_batch1_isolated_defect_properties(pilot_cases):
    """Verify detailed properties of all 6 Batch 1 ground-truth records."""
    case_map = {c.case_id: c for c in pilot_cases}
    assert "CAND-0006" in case_map
    assert "CAND-0008" in case_map
    assert "CAND-0015" in case_map
    assert "CAND-0020" in case_map
    assert "CAND-0026" in case_map
    assert "CAND-0033" in case_map

    # CAND-0006: Category 1 functional defect in Scrapy (pre-fix lines 318-319, verified in Phase 3C)
    c6 = case_map["CAND-0006"]
    assert c6.repository == "scrapy/scrapy"
    assert c6.verification_status == "GROUND_TRUTH_VERIFIED"
    assert c6.reproducer_status == ReproducerStatus.EXECUTED_CONFIRMED
    assert c6.defects[0].file_path == "scrapy/utils/datatypes.py"
    assert (c6.defects[0].start_line, c6.defects[0].end_line) == (318, 319)
    assert c6.defects[0].impact == ImpactType.FUNCTIONAL
    assert c6.defects[0].primary_cwe == "CWE-476"
    assert c6.defects[0].acceptable_alternative_cwes == {"CWE-670"}

    # CAND-0008: Category 2 ReDoS in python-multipart (1 defect, executed confirmed)
    c8 = case_map["CAND-0008"]
    assert c8.repository == "Kludex/python-multipart"
    assert c8.verification_status == "GROUND_TRUTH_VERIFIED"
    assert c8.reproducer_status == ReproducerStatus.EXECUTED_CONFIRMED
    assert len(c8.defects) == 1
    assert (c8.defects[0].start_line, c8.defects[0].end_line) == (72, 75)
    assert c8.defects[0].primary_cwe == "CWE-1333"
    assert c8.defects[0].acceptable_alternative_cwes == {"CWE-400"}

    # CAND-0015: Category 3 SQL injection in Django StringAgg
    c15 = case_map["CAND-0015"]
    assert c15.repository == "django/django"
    assert c15.verification_status == "GROUND_TRUTH_VERIFIED"
    assert c15.reproducer_status == ReproducerStatus.CITED_NOT_RUN
    assert (c15.defects[0].start_line, c15.defects[0].end_line) == (54, 58)
    assert c15.defects[0].primary_cwe == "CWE-89"
    assert c15.defects[0].acceptable_alternative_cwes == {"CWE-943"}

    # CAND-0020: Category 4 Path traversal in Werkzeug safe_join
    c20 = case_map["CAND-0020"]
    assert c20.repository == "pallets/werkzeug"
    assert c20.verification_status == "GROUND_TRUTH_VERIFIED"
    assert c20.reproducer_status == ReproducerStatus.ATTEMPTED_BLOCKED
    assert (c20.defects[0].start_line, c20.defects[0].end_line) == (151, 157)
    assert c20.defects[0].primary_cwe == "CWE-22"
    assert c20.defects[0].acceptable_alternative_cwes == {"CWE-20"}

    # CAND-0026: Category 5 Auth state bypass in Paramiko (1 matchable defect, 1 contextual file)
    c26 = case_map["CAND-0026"]
    assert c26.repository == "paramiko/paramiko"
    assert c26.verification_status == "GROUND_TRUTH_VERIFIED"
    assert c26.reproducer_status == ReproducerStatus.CITED_NOT_RUN
    assert c26.contextual_files == ["paramiko/common.py"]
    assert len(c26.defects) == 1
    assert (c26.defects[0].start_line, c26.defects[0].end_line) == (1822, 1828)
    assert c26.defects[0].primary_cwe == "CWE-287"
    assert c26.defects[0].acceptable_alternative_cwes == {"CWE-305"}

    # CAND-0033: Category 6 Missing authz in Zulip typing endpoint
    c33 = case_map["CAND-0033"]
    assert c33.repository == "zulip/zulip"
    assert c33.verification_status == "GROUND_TRUTH_VERIFIED"
    assert c33.reproducer_status == ReproducerStatus.CITED_NOT_RUN
    assert (c33.defects[0].start_line, c33.defects[0].end_line) == (83, 85)
    assert c33.defects[0].primary_cwe == "CWE-863"
    assert c33.defects[0].acceptable_alternative_cwes == {"CWE-639"}


def test_reproducer_status_enum_validation():
    """Verify reproducer_status validates defined enum values and rejects invalid strings."""
    valid_statuses = [
        "executed_confirmed",
        "executed_not_reproduced",
        "attempted_blocked",
        "cited_not_run",
        "historical_claim_unverified",
        "not_attempted",
    ]
    for status_str in valid_statuses:
        case = BenchmarkCase(
            case_id="CAND-TEST",
            repository="owner/repo",
            commit_hash="a" * 40,
            is_buggy=False,
            reproducer_status=status_str,
        )
        assert case.reproducer_status == status_str

    with pytest.raises(ValidationError):
        BenchmarkCase(
            case_id="CAND-TEST-INV",
            repository="owner/repo",
            commit_hash="a" * 40,
            is_buggy=False,
            reproducer_status="invalid_status_value",
        )


def test_canonical_records_load_with_statuses(pilot_cases):
    """Verify all canonical cases load with recorded verification and reproducer statuses."""
    assert len(pilot_cases) == 18
    pilot_12_ids = {
        "CAND-0001",
        "CAND-0002",
        "CAND-0007",
        "CAND-0009",
        "CAND-0014",
        "CAND-0017",
        "CAND-0019",
        "CAND-0021",
        "CAND-0025",
        "CAND-0027",
        "CAND-0031",
        "CAND-0032",
    }
    case_map = {c.case_id: c for c in pilot_cases}
    for pid in pilot_12_ids:
        c = case_map[pid]
        assert c.verification_status == "GROUND_TRUTH_VERIFIED"
        assert c.reproducer_status == ReproducerStatus.HISTORICAL_CLAIM_UNVERIFIED


def test_contextual_files_isolation_from_targets_and_defects(pilot_cases):
    """Verify contextual files never become matchable target files or defects."""
    for case in pilot_cases:
        if case.contextual_files:
            defect_files = {d.file_path for d in case.defects}
            for ctx_file in case.contextual_files:
                assert ctx_file not in defect_files, (
                    f"Contextual file '{ctx_file}' in '{case.case_id}' must not appear as a defect target!"
                )
    # Paramiko specific check
    paramiko_case = next(c for c in pilot_cases if c.case_id == "CAND-0026")
    assert paramiko_case.contextual_files == ["paramiko/common.py"]
    assert paramiko_case.defects[0].file_path == "paramiko/transport.py"
    assert "paramiko/common.py" not in [d.file_path for d in paramiko_case.defects]


def test_deterministic_census_calculation_from_canonical_data():
    """Verify census statistics are dynamically computed from canonical data."""
    census = compute_census()
    can = census["canonical"]
    q = census["queue"]

    # Canonical dataset expectations
    assert can["case_count"] == 18
    assert can["verification_status_counts"]["GROUND_TRUTH_VERIFIED"] == 18
    assert can["verification_status_counts"].get("SOURCE_VERIFIED", 0) == 0
    assert can["total_defects"] == 23
    assert can["gt_verified_defects"] == 23
    assert can["source_verified_defects"] == 0
    assert can["distinct_target_files_count"] == 17
    assert can["distinct_contextual_files_count"] == 1
    assert can["distinct_contextual_files"] == ["paramiko/common.py"]
    assert can["file_union_count"] == 18
    assert can["distinct_loci_count"] == 23

    # Staging queue expectations
    assert q["total_staged_candidates"] == 36
    assert q["lifecycle_counts"]["GROUND_TRUTH_VERIFIED"] == 19
    assert q["lifecycle_counts"]["SOURCE_VERIFIED"] == 17
    assert q["rejected_leads_count"] == 7
    assert q["accepted_into_benchmark"] == 0


def test_only_verified_loader_filter():
    """Verify only_verified filter in load_pilot_cases_from_json returns strictly verified cases."""
    all_cases = load_pilot_cases_from_json(only_verified=False)
    assert len(all_cases) == 18

    verified_cases = load_pilot_cases_from_json(only_verified=True)
    assert len(verified_cases) == 18
    assert all(c.verification_status == "GROUND_TRUTH_VERIFIED" for c in verified_cases)

    verified_ids = {c.case_id for c in verified_cases}
    assert "CAND-0006" in verified_ids
    assert "CAND-0008" in verified_ids


def test_pilot_summary_table_parity_with_canonical_dataset():
    """Verify strict locus parity between ground_truth_validation_pilot.md Table 1 and canonical JSON."""
    table_path = Path("Project Documents/dataset/ground_truth_validation_pilot.md")
    with open(table_path, encoding="utf-8") as f:
        text = f.read()

    # Parse Table 1 rows: | **CAND-XXXX** | Cat X: ... | repo | file | locus | ...
    table_rows = re.findall(
        r"\|\s*\*\*(CAND-\d{4})\*\*\s*\|[^|]*\|[^|]*\|[^|]*\|\s*([^|]+)\s*\|",
        text,
    )
    assert len(table_rows) == 12, f"Expected 12 pilot cases in Table 1, found {len(table_rows)}"

    canonical_cases = load_pilot_cases_from_json(only_verified=False)
    case_map = {c.case_id: c for c in canonical_cases}

    for cand_id, locus_raw in table_rows:
        assert cand_id in case_map
        case = case_map[cand_id]
        parsed_ranges = [tuple(r) for r in parse_ground_truth_locus(locus_raw)]
        canonical_ranges = [(d.start_line, d.end_line) for d in case.defects]
        assert set(parsed_ranges) == set(canonical_ranges), (
            f"Locus mismatch for {cand_id}: Table 1 has {parsed_ranges}, canonical JSON has {canonical_ranges}"
        )


def test_importer_locus_parsing_and_subsumption():
    """Verify parse_ground_truth_locus correctly parses ranges, strips incidental notes, and handles subsumption."""
    # 1. Strips parenthetical explanatory notes and incidental line mentions
    raw_cand1 = 'Lines 390–394 (specifically line 393: `and "Transfer-Encoding" not in headers`)'
    assert parse_ground_truth_locus(raw_cand1) == [[390, 394]]

    # 2. Preserves multiple distinct disjoint loci
    raw_cand9 = "Line 250 (_space_re definition) and Lines 292–293 (validation check)"
    assert parse_ground_truth_locus(raw_cand9) == [[250, 250], [292, 293]]

    raw_cand14 = "Lines 45–51 (Extract.__init__) and Lines 225–236 (Trunc.__init__)"
    assert parse_ground_truth_locus(raw_cand14) == [[45, 51], [225, 236]]

    # 3. Preserves CAND-0032 distinct authorization loci
    raw_cand32 = "Lines 825–827 (if has_user_message) and Lines 842–856 (in has_message_access)"
    assert parse_ground_truth_locus(raw_cand32) == [[825, 827], [842, 856]]

    # 4. Table cell comma/en-dash format without 'Lines' prefix
    raw_table_cell = "250, 292–293"
    assert parse_ground_truth_locus(raw_table_cell) == [[250, 250], [292, 293]]

    # 5. Subsumption: narrower range falling entirely within a broader range is eliminated
    raw_with_subsumption = "Lines 100–120 and Line 105"
    assert parse_ground_truth_locus(raw_with_subsumption) == [[100, 120]]

    # 6. Broader range arriving second subsumes previously added narrower range
    raw_reverse_subsumption = "Line 105 and Lines 100–120"
    assert parse_ground_truth_locus(raw_reverse_subsumption) == [[100, 120]]

    # 7. Non-subsumed distinct spans (e.g. partial overlaps or adjacent spans)
    raw_partial = "Lines 50–60 and Lines 55–65"
    assert parse_ground_truth_locus(raw_partial) == [[50, 60], [55, 65]]

    # 8. Duplicate rejection on valid ranges
    raw_identical_duplicate = "Lines 100–120 and Lines 100–120"
    assert parse_ground_truth_locus(raw_identical_duplicate) == [[100, 120]]

    raw_dup_single = "Line 42 and Line 42"
    assert parse_ground_truth_locus(raw_dup_single) == [[42, 42]]

    # 9. Multiple duplicates mixed with subsumption
    raw_mixed_duplicates = "Lines 10–20, Line 15, Lines 10–20, Line 10"
    assert parse_ground_truth_locus(raw_mixed_duplicates) == [[10, 20]]

    # 10. Inverted / reversed range normalization and deduplication
    raw_inverted = "Lines 120–100"
    assert parse_ground_truth_locus(raw_inverted) == [[100, 120]]

    raw_inverted_and_standard = "Lines 100–120 and Lines 120–100"
    assert parse_ground_truth_locus(raw_inverted_and_standard) == [[100, 120]]

    # 11. Invalid ranges, non-numeric strings, and whitespace
    assert parse_ground_truth_locus("No specific line numbers") == []
    assert parse_ground_truth_locus("Lines abc-def") == []
    assert parse_ground_truth_locus("   \t\n   ") == []
    assert parse_ground_truth_locus("") == []
    assert parse_ground_truth_locus(None) == []
