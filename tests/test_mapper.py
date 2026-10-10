"""Unit tests for static analysis FindingMapper and ruleset manifest resolution."""

import pytest

from auditor.models.finding import DetectionLayer, SeverityLevel
from auditor.static_analysis.mapper import FindingMapper


@pytest.fixture
def mapper():
    return FindingMapper()


def test_map_ruff_known_rule_s105(mapper: FindingMapper):
    raw = {
        "code": "S105",
        "message": 'Possible hardcoded password assigned to: "admin"',
        "location": {"row": 10, "column": 5},
        "end_location": {"row": 10, "column": 25},
        "url": "https://docs.astral.sh/ruff/rules/hardcoded-password-string",
    }
    pred = mapper.map_ruff_finding(raw, "app/auth.py")

    assert pred.tool_name == "ruff"
    assert pred.detection_layer == DetectionLayer.DETERMINISTIC_STATIC
    assert pred.category_id == 5  # Category 5: Authentication
    assert pred.primary_cwe == "CWE-798"
    assert "CWE-259" in pred.alternative_cwes
    assert pred.file_path == "app/auth.py"
    assert pred.start_line == 10
    assert pred.end_line == 10


def test_map_ruff_known_rule_s608(mapper: FindingMapper):
    raw = {
        "code": "S608",
        "message": "Possible SQL injection vector through string-based query construction",
        "location": {"row": 42, "column": 1},
        "end_location": {"row": 42, "column": 50},
    }
    pred = mapper.map_ruff_finding(raw, "db/query.py")

    assert pred.category_id == 3  # Category 3: SQL / ORM Injection
    assert pred.primary_cwe == "CWE-89"
    assert "CWE-943" in pred.alternative_cwes
    assert pred.start_line == 42


def test_map_semgrep_known_rule(mapper: FindingMapper):
    raw = {
        "check_id": "python.django.security.injection.sql.sql-injection-using-db-cursor-execute.sql-injection-db-cursor-execute",
        "start": {"line": 15, "col": 1},
        "end": {"line": 15, "col": 40},
        "extra": {
            "severity": "ERROR",
            "message": "Detected SQL injection in db cursor execute call",
            "metadata": {"cwe": ["CWE-89: SQL Injection"]},
        },
    }
    pred = mapper.map_semgrep_finding(raw, "views/users.py")

    assert pred.tool_name == "semgrep"
    assert pred.detection_layer == DetectionLayer.DETERMINISTIC_STATIC
    assert pred.category_id == 3
    assert pred.primary_cwe == "CWE-89"
    assert pred.severity == SeverityLevel.HIGH
    assert pred.start_line == 15
    assert pred.end_line == 15


def test_map_unmapped_rule_fallback(mapper: FindingMapper):
    raw = {
        "code": "UNKNOWN_RULE_999",
        "message": "Some custom unknown checker violation",
        "location": {"row": 1, "column": 1},
        "end_location": {"row": 1, "column": 10},
    }
    pred = mapper.map_ruff_finding(raw, "test.py")

    # Unmapped policy: category_id=1, primary_cwe='CWE-UNMAPPED', scored as FP
    assert pred.category_id == 1
    assert pred.primary_cwe == "CWE-UNMAPPED"
    assert pred.provenance.get("is_unmapped") is True
