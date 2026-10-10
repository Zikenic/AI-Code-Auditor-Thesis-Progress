"""Unit tests for Configuration B pipeline, chunker, parser, deduplication, and budget ledger."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditor.llm.chunker import SourceChunker
from auditor.llm.cost_tracker import CostTracker
from auditor.llm.deduplication import deduplicate_findings
from auditor.llm.engine import ConfigBAuditEngine, ILlmApiClient
from auditor.llm.parser import ConfigBResponseParser
from auditor.llm.prompt_builder import assert_zero_answer_leakage
from auditor.models.finding import (
    DetectionLayer,
    PredictedFinding,
    SeverityLevel,
)
from auditor.models.result import AuditStatus


# ---------------------------------------------------------
# Synthetic API Client Mock
# ---------------------------------------------------------
class MockLlmApiClient(ILlmApiClient):
    def __init__(self, responses: list[tuple[str, int, int]] | None = None, raise_error: bool = False):
        self.responses = list(responses or [])
        self.call_count = 0
        self.raise_error = raise_error
        self.captured_prompts: list[dict[str, str]] = []

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        model_id: str,
        thinking_type: str = "adaptive",
        thinking_effort: str = "medium",
    ) -> tuple[str, int, int]:
        self.call_count += 1
        self.captured_prompts.append({"system": system_prompt, "user": user_prompt})
        if self.raise_error:
            raise RuntimeError("Synthetic simulated API error")
        if self.responses:
            return self.responses.pop(0)
        return json.dumps({"findings": []}), 100, 50


# ---------------------------------------------------------
# Test Chunker (Tiers 1, 2, 3 and Invariants)
# ---------------------------------------------------------
def test_chunker_tier1_single_pass():
    code = "def add(a, b):\n    return a + b\n"
    chunker = SourceChunker(token_budget=16000)
    chunks = chunker.chunk_source(code, "math_utils.py")

    assert len(chunks) == 1
    c = chunks[0]
    assert c.tier == 1
    assert c.start_line == 1
    assert c.end_line == 2
    assert c.total_lines == 2
    assert "1: def add(a, b):" in c.rendered_text
    assert "2:     return a + b" in c.rendered_text


def test_chunker_tier2_ast_chunking():
    # Construct multi-class code that exceeds a small budget of 80 tokens
    code = (
        "import sys\n"
        "import os\n\n"
        "class FirstHandler:\n"
        "    def handle(self):\n"
        "        pass\n\n"
        "class SecondHandler:\n"
        "    def process(self):\n"
        "        pass\n\n"
        "class ThirdHandler:\n"
        "    def execute(self):\n"
        "        pass\n"
    )
    # Small budget forcing multiple chunks
    chunker = SourceChunker(token_budget=70)
    chunks = chunker.chunk_source(code, "handlers.py")

    assert len(chunks) >= 2
    for c in chunks:
        assert c.tier in (2, 3)
    # Verify INV-03: complete line coverage
    assert chunks[0].start_line == 1
    assert chunks[-1].end_line == len(code.splitlines())


def test_chunker_tier3_fallback_on_syntax_error():
    # Syntax error with non-Python text
    bad_code = "def invalid syntax {{{ :: %%%\n" * 50
    chunker = SourceChunker(token_budget=60)
    chunks = chunker.chunk_source(bad_code, "bad.py")

    assert len(chunks) >= 2
    assert chunks[0].tier == 3
    # Check INV-03 coverage
    assert chunks[0].start_line == 1
    assert chunks[-1].end_line == 50


# ---------------------------------------------------------
# Test Response Parser
# ---------------------------------------------------------
def test_parser_valid_json():
    parser = ConfigBResponseParser()
    raw = json.dumps(
        {
            "findings": [
                {
                    "file_path": "foo/bar.py",
                    "start_line": 10,
                    "end_line": 12,
                    "category_id": 1,
                    "primary_cwe": "CWE-476",
                    "alternative_cwes": ["CWE-670"],
                    "severity": "high",
                    "confidence": "high",
                    "title": "NoneType dereference",
                    "description": "Variable can be None",
                    "category_1_impact": "unhandled_exception",
                }
            ]
        }
    )
    findings = parser.parse_response(raw, "foo/bar.py", total_file_lines=100)
    assert len(findings) == 1
    f = findings[0]
    assert f.file_path == "foo/bar.py"
    assert f.start_line == 10
    assert f.end_line == 12
    assert f.category_id == 1
    assert f.primary_cwe == "CWE-476"
    assert f.alternative_cwes == ["CWE-670"]
    assert f.severity == SeverityLevel.HIGH
    assert f.provenance["category_1_impact"] == "unhandled_exception"


def test_parser_markdown_fence_stripping():
    parser = ConfigBResponseParser()
    raw = (
        "Here are my findings:\n```json\n"
        "{\n"
        '  "findings": [\n'
        "    {\n"
        '      "file_path": "a/b.py",\n'
        '      "start_line": 5,\n'
        '      "category_id": 2,\n'
        '      "primary_cwe": "89",\n'
        '      "title": "SQL Injection",\n'
        '      "description": "Unsanitized input"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "```\nThank you!"
    )
    findings = parser.parse_response(raw, "a/b.py", total_file_lines=50)
    assert len(findings) == 1
    assert findings[0].primary_cwe == "CWE-89"
    assert findings[0].category_id == 2
    assert findings[0].start_line == 5
    assert findings[0].end_line == 5


def test_parser_coordinate_validation_inv06():
    parser = ConfigBResponseParser()
    # Out of bounds cases: start_line > total_lines or start_line < 1
    raw = json.dumps(
        {
            "findings": [
                {
                    "file_path": "test.py",
                    "start_line": 150,  # exceeds total lines 100
                    "end_line": 160,
                    "category_id": 1,
                    "primary_cwe": "CWE-476",
                    "title": "Bad",
                    "description": "Bad",
                },
                {
                    "file_path": "test.py",
                    "start_line": 0,  # < 1
                    "end_line": 5,
                    "category_id": 1,
                    "primary_cwe": "CWE-476",
                    "title": "Bad 2",
                    "description": "Bad 2",
                },
                {
                    "file_path": "test.py",
                    "start_line": 10,
                    "end_line": 5,  # end < start
                    "category_id": 1,
                    "primary_cwe": "CWE-476",
                    "title": "Bad 3",
                    "description": "Bad 3",
                },
                {
                    "file_path": "test.py",
                    "start_line": 10,
                    "end_line": 15,  # valid
                    "category_id": 1,
                    "primary_cwe": "CWE-476",
                    "title": "Good",
                    "description": "Good",
                },
            ]
        }
    )
    findings = parser.parse_response(raw, "test.py", total_file_lines=100)
    assert len(findings) == 1
    assert findings[0].title == "Good"


# ---------------------------------------------------------
# Test Deduplication (INV-07)
# ---------------------------------------------------------
def test_deduplication_preserves_distinct_cwes():
    f1 = PredictedFinding(
        finding_id="f1",
        detection_layer=DetectionLayer.HEURISTIC_LLM,
        tool_name="test",
        category_id=1,
        primary_cwe="CWE-476",
        file_path="pkg/module.py",
        start_line=20,
        end_line=25,
        title="Flaw 1",
        description="Desc 1",
    )
    f2 = PredictedFinding(
        finding_id="f2",
        detection_layer=DetectionLayer.HEURISTIC_LLM,
        tool_name="test",
        category_id=1,
        primary_cwe="CWE-670",  # Distinct CWE at same lines
        file_path="pkg/module.py",
        start_line=20,
        end_line=25,
        title="Flaw 2",
        description="Desc 2",
    )
    f3 = PredictedFinding(
        finding_id="f3",
        detection_layer=DetectionLayer.HEURISTIC_LLM,
        tool_name="test",
        category_id=1,
        primary_cwe="CWE-476",  # Duplicate of f1
        file_path="pkg/module.py",
        start_line=20,
        end_line=25,
        title="Flaw 1 dup",
        description="Desc 1 dup",
    )

    deduped = deduplicate_findings([f1, f2, f3])
    assert len(deduped) == 2
    assert {f.primary_cwe for f in deduped} == {"CWE-476", "CWE-670"}


# ---------------------------------------------------------
# Test Cost Tracker & Budget Ceiling Guard
# ---------------------------------------------------------
def test_cost_tracker_calculation_and_ceiling(tmp_path: Path):
    ledger = tmp_path / "ledger.json"
    tracker = CostTracker(budget_ceiling_usd=1.00, ledger_path=ledger)

    # 10,000 prompt tokens ($3/M) = $0.03
    # 2,000 completion tokens ($15/M) = $0.03
    rec = tracker.record_usage("CAND-TEST", 1, 10_000, 2_000, 1.5, "claude-sonnet-5-5")
    assert round(rec.cost_usd, 3) == 0.06
    assert round(tracker.total_cost(), 3) == 0.06
    assert ledger.exists()

    # Verify would_exceed_ceiling
    # Trying to allocate 500,000 completion tokens ($7.50)
    assert tracker.would_exceed_ceiling(10_000, 500_000) is True
    # Trying to allocate 1,000 completion tokens
    assert tracker.would_exceed_ceiling(10_000, 1_000) is False


# ---------------------------------------------------------
# Test Engine Partial-Run Discard Policy (FR-09)
# ---------------------------------------------------------
def test_engine_discards_on_chunk_failure():
    # Provide two responses, but mock raises error on second
    client = MockLlmApiClient(raise_error=True)
    engine = ConfigBAuditEngine(api_client=client)

    code = "x = 1\n" * 10
    status, findings, meta = engine.audit_source(code, "foo.py")

    # When API fails, FR-09 enforces: 0 findings emitted, status FAILED
    assert status == AuditStatus.FAILED
    assert len(findings) == 0
    assert "error" in meta


# ---------------------------------------------------------
# Test Ground-Truth Leakage Guard (INV-09)
# ---------------------------------------------------------
def test_leakage_guard():
    with pytest.raises(ValueError, match="CRITICAL: Answer leakage detected"):
        assert_zero_answer_leakage(
            "Here is CVE-2023-1234 fixed in commit abc123def",
            forbidden_terms=["CVE-2023-1234", "abc123def"],
        )
