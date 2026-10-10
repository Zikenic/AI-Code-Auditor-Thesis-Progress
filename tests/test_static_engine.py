"""Unit and integration tests for StaticAnalysisEngine."""

import tempfile
from pathlib import Path

import pytest

from auditor.models.finding import DetectionLayer, PredictedFinding
from auditor.static_analysis.engine import (
    StaticAnalysisEngine,
    deduplicate_static_findings,
)


@pytest.fixture
def engine():
    return StaticAnalysisEngine()


def test_static_engine_detects_hardcoded_password(engine: StaticAnalysisEngine):
    code = 'DATABASE_PASSWORD = "super_secret_admin_password_12345"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        target = root / "config.py"
        target.write_text(code, encoding="utf-8")

        findings = engine.run_static_analysis(str(root), ["config.py"])

        assert len(findings) >= 1
        f = findings[0]
        assert f.detection_layer == DetectionLayer.DETERMINISTIC_STATIC
        assert f.category_id == 5  # Authentication
        assert f.primary_cwe == "CWE-798"
        assert f.file_path == "config.py"
        assert f.start_line == 1


def test_static_engine_detects_sql_injection(engine: StaticAnalysisEngine):
    code = 'def get_user(uid):\n    query = "SELECT * FROM users WHERE id = \'" + uid + "\'"\n    return query\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        target = root / "db.py"
        target.write_text(code, encoding="utf-8")

        findings = engine.run_static_analysis(str(root), ["db.py"])

        sql_findings = [f for f in findings if f.category_id == 3 or f.primary_cwe == "CWE-89"]
        assert len(sql_findings) >= 1
        assert sql_findings[0].file_path == "db.py"
        assert sql_findings[0].start_line == 2


def test_static_engine_suppression_isolation_noqa_and_nosemgrep(engine: StaticAnalysisEngine):
    """Adversarial test: source code containing inline suppressions must NOT suppress findings."""
    code = (
        'DATABASE_PASSWORD = "hardcoded_password_123"  # noqa: S105\n'
        'query = "SELECT * FROM users WHERE id = \'" + uid + "\'"  # noqa: S608  # nosemgrep\n'
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        target = root / "secure.py"
        target.write_text(code, encoding="utf-8")

        findings = engine.run_static_analysis(str(root), ["secure.py"])

        # Findings must be detected despite # noqa and # nosemgrep
        cwes = {f.primary_cwe for f in findings}
        assert "CWE-798" in cwes or "CWE-89" in cwes


def test_static_engine_repo_config_and_ignore_isolation(engine: StaticAnalysisEngine):
    """Adversarial test: target repository configs and ignore files must NOT suppress findings."""
    code = 'ADMIN_PASS = "admin123456"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        target = root / "src" / "admin.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code, encoding="utf-8")

        # Repository adversarial config files trying to suppress S105 and ignore src/
        (root / "ruff.toml").write_text('[lint]\nignore = ["S105"]\n', encoding="utf-8")
        (root / ".semgrepignore").write_text("src/**\n", encoding="utf-8")
        (root / ".gitignore").write_text("src/**\n", encoding="utf-8")

        findings = engine.run_static_analysis(str(root), ["src/admin.py"])

        assert len(findings) >= 1
        assert any(f.primary_cwe == "CWE-798" for f in findings)
        assert any(f.file_path == "src/admin.py" for f in findings)


def test_static_engine_skips_non_python_files(engine: StaticAnalysisEngine):
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "README.md").write_text("# Documentation\n", encoding="utf-8")
        (root / "config.json").write_text('{"key": "value"}\n', encoding="utf-8")

        findings = engine.run_static_analysis(str(root), ["README.md", "config.json"])
        assert findings == []


def test_static_engine_handles_syntax_error_gracefully(engine: StaticAnalysisEngine):
    code = "def broken_syntax(:\n    pass\n"
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "broken.py").write_text(code, encoding="utf-8")

        # Must not raise an unhandled exception or crash the pipeline
        findings = engine.run_static_analysis(str(root), ["broken.py"])
        assert isinstance(findings, list)


def test_deduplicate_static_findings():
    f1 = PredictedFinding(
        finding_id="f1",
        detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
        tool_name="ruff",
        category_id=3,
        primary_cwe="CWE-89",
        file_path="app.py",
        start_line=10,
        end_line=10,
        title="SQL injection ruff",
        description="SQL injection ruff",
    )
    f2 = PredictedFinding(
        finding_id="f2",
        detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
        tool_name="semgrep",
        category_id=3,
        primary_cwe="CWE-89",
        file_path="app.py",
        start_line=10,
        end_line=10,
        title="SQL injection semgrep",
        description="SQL injection semgrep",
    )
    f3 = PredictedFinding(
        finding_id="f3",
        detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
        tool_name="ruff",
        category_id=5,
        primary_cwe="CWE-798",
        file_path="app.py",
        start_line=25,
        end_line=25,
        title="Hardcoded secret",
        description="Hardcoded secret",
    )

    deduped = deduplicate_static_findings([f1, f2, f3])
    assert len(deduped) == 2
    merged = [f for f in deduped if f.primary_cwe == "CWE-89"][0]
    assert "ruff" in merged.provenance.get("tools", [])
    assert "semgrep" in merged.provenance.get("tools", [])


def test_deduplicate_preserves_distinct_cwes_at_same_line():
    """Ensure that findings with different CWEs at the exact same line are NOT merged or dropped."""
    f1 = PredictedFinding(
        finding_id="f1",
        detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
        tool_name="ruff",
        category_id=1,
        primary_cwe="CWE-670",
        file_path="service.py",
        start_line=50,
        end_line=50,
        title="Logic issue",
        description="Logic issue",
    )
    f2 = PredictedFinding(
        finding_id="f2",
        detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
        tool_name="semgrep",
        category_id=3,
        primary_cwe="CWE-89",
        file_path="service.py",
        start_line=50,
        end_line=50,
        title="SQL Injection",
        description="SQL Injection",
    )

    deduped = deduplicate_static_findings([f1, f2])
    assert len(deduped) == 2
    cwes = {f.primary_cwe for f in deduped}
    assert cwes == {"CWE-670", "CWE-89"}
