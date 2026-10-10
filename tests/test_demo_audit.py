"""Tests for the local repository demonstration entrypoint (tools/demo_audit.py)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from auditor.models.finding import (
    ConfidenceLevel,
    DetectionLayer,
    PredictedFinding,
    SeverityLevel,
)
from tools.demo_audit import (
    discover_python_files,
    format_finding_card,
    main,
    run_demo,
)


def test_discover_python_files_single_file(tmp_path: Path):
    py_file = tmp_path / "sample.py"
    py_file.write_text("x = 1\n", encoding="utf-8")
    assert discover_python_files(py_file) == ["sample.py"]

    non_py = tmp_path / "sample.txt"
    non_py.write_text("hello\n", encoding="utf-8")
    assert discover_python_files(non_py) == []


def test_discover_python_files_directory(tmp_path: Path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("assert True\n", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "ignored.py").write_text("pass\n", encoding="utf-8")

    files = discover_python_files(tmp_path)
    assert "app/main.py" in files
    assert "tests/test_main.py" in files
    assert ".venv/ignored.py" not in files


def test_format_finding_card():
    f = PredictedFinding(
        finding_id="find-123",
        detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
        tool_name="ruff",
        category_id=1,
        primary_cwe="CWE-670",
        file_path="src/app.py",
        start_line=10,
        end_line=12,
        severity=SeverityLevel.HIGH,
        confidence=ConfidenceLevel.HIGH,
        title="Sample Defect",
        description="Detailed explanation",
        suggestion="Fix suggestion",
        provenance={"rule_code": "S101"},
    )
    card = format_finding_card(f, 1)
    assert "[01] Sample Defect" in card
    assert "src/app.py:10-12" in card
    assert "RUFF | S101" in card
    assert "Category 1 (CWE-670)" in card
    assert "HIGH" in card
    assert "Fix suggestion" in card


def test_run_demo_nonexistent_path(tmp_path: Path, capsys: pytest.CaptureFixture):
    bad_path = tmp_path / "does_not_exist"
    code, findings = run_demo(bad_path)
    assert code == 1
    assert findings == []
    captured = capsys.readouterr()
    assert "does not exist" in captured.err


def test_run_demo_empty_findings(tmp_path: Path, capsys: pytest.CaptureFixture):
    py_file = tmp_path / "clean.py"
    py_file.write_text("x = 1\n", encoding="utf-8")

    mock_engine = MagicMock()
    mock_engine.run_static_analysis.return_value = []

    code, findings = run_demo(py_file, engine=mock_engine)
    assert code == 0
    assert findings == []
    captured = capsys.readouterr()
    assert "Zero findings detected" in captured.out


def test_run_demo_analysis_failure(tmp_path: Path, capsys: pytest.CaptureFixture):
    py_file = tmp_path / "err.py"
    py_file.write_text("x = 1\n", encoding="utf-8")

    mock_engine = MagicMock()
    mock_engine.run_static_analysis.side_effect = RuntimeError("Subprocess crash")

    code, findings = run_demo(py_file, engine=mock_engine)
    assert code == 2
    assert findings == []
    captured = capsys.readouterr()
    assert "Analysis failure: Subprocess crash" in captured.err


def test_main_cli_argument(tmp_path: Path):
    py_file = tmp_path / "clean.py"
    py_file.write_text("x = 1\n", encoding="utf-8")

    code = main([str(py_file)])
    assert code == 0
