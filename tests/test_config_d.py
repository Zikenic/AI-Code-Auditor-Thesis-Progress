"""Tests for Configuration D: context retrieval, prompt assembly, and isolation invariants."""

from __future__ import annotations

from pathlib import Path

import pytest

from auditor.llm.chunker import SourceChunk
from auditor.llm.context_retriever import RepositoryIndex
from auditor.llm.prompt_builder import (
    assert_zero_answer_leakage,
    build_config_d_user_prompt,
    get_system_prompt,
)


@pytest.fixture
def mock_repo_index():
    """Create a mock repository index structure."""
    idx = RepositoryIndex.__new__(RepositoryIndex)
    idx.repo_dir = Path(".")
    idx.commit_hash = "mockcommit"
    idx.files = {
        "auth/helpers.py": "def check_token(token):\n    return token == 'valid'\n",
        "models/base.py": "class BaseModel:\n    def save(self):\n        pass\n",
        "views/target.py": "from auth.helpers import check_token\nfrom models.base import BaseModel\nclass MyView(BaseModel):\n    def handle(self):\n        check_token('foo')\n",
    }
    idx.symbol_table = {
        "check_token": [("auth/helpers.py", 1, 2)],
        "BaseModel": [("models/base.py", 1, 3)],
        "save": [("models/base.py", 2, 3)],
    }
    idx.classes = {
        "BaseModel": ("models/base.py", 1, 3, []),
    }
    return idx


def test_system_prompt_retrieval_config_d():
    sys_prompt = get_system_prompt("D")
    assert "TAXONOMY OF DEFECTS" in sys_prompt
    assert "Category 1" in sys_prompt
    assert "Category 6" in sys_prompt
    assert "AUDIT TARGET" in sys_prompt


def test_config_d_user_prompt_assembly():
    chunk = SourceChunk(
        file_path="tornado/http1connection.py",
        chunk_index=1,
        total_chunks=1,
        start_line=1,
        end_line=50,
        total_lines=100,
        rendered_text="=== AUDIT TARGET: tornado/http1connection.py (Lines 1 to 50 of 100) ===\n1: x = 1\n=== END AUDIT TARGET ===",
        raw_code="x = 1\n",
        token_estimate=20,
        tier=1,
        scope_description="Whole-file test",
    )
    static_section = "### DETECTED STATIC ANALYSIS FINDINGS (FOR REFERENCE ONLY)\n- Finding 1: Ruff S101"
    context_section = "### REPOSITORY CONTEXT EXCERPTS (FOR REFERENCE ONLY)\n--- CONTEXT: helper.py ---"

    prompt = build_config_d_user_prompt(chunk, static_section=static_section, context_section=context_section)
    assert "=== AUDIT TARGET:" in prompt
    assert "DETECTED STATIC ANALYSIS FINDINGS" in prompt
    assert "REPOSITORY CONTEXT EXCERPTS" in prompt
    assert "Identify all concrete security vulnerabilities" in prompt


def test_zero_leakage_assertion():
    clean_prompt = "Audit this code:\n1: def foo(): return 42"
    assert_zero_answer_leakage(clean_prompt, forbidden_terms=["CVE-2023-1234", "CAND-0001-DEF-1"])

    with pytest.raises(ValueError, match="Answer leakage detected"):
        leak_prompt = "Audit this code with CVE-2023-1234 present"
        assert_zero_answer_leakage(leak_prompt, forbidden_terms=["CVE-2023-1234"])


def test_context_retriever_query_extraction(mock_repo_index):
    from auditor.llm.context_retriever import RepositoryContextRetriever

    retriever = RepositoryContextRetriever(mock_repo_index)
    target_code = "from auth.helpers import check_token\nfrom models.base import BaseModel\nclass MyView(BaseModel):\n    def handle(self):\n        check_token('foo')\n"

    section, items, omitted = retriever.retrieve_context(
        target_file="views/target.py",
        chunk_start=1,
        chunk_end=10,
        chunk_code=target_code,
        max_tokens=2000,
    )

    assert len(items) >= 2
    paths = [item.file_path for item in items]
    assert "auth/helpers.py" in paths
    assert "models/base.py" in paths
    # Hard rule: Target file/chunk itself is NOT in retrieved context
    assert "views/target.py" not in paths
    assert "REPOSITORY CONTEXT EXCERPTS" in section


def test_prefix_only_indexing(tmp_path):
    """Verify index is constructed from the recorded pre-fix Git tree, not fix commit or working tree."""
    import subprocess

    from auditor.llm.context_retriever import RepositoryIndex

    # Create a local test git repository
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)

    # Pre-fix commit C_buggy
    (repo_dir / "vuln.py").write_text("def bug():\n    return 'unpatched'\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "pre-fix buggy state"], cwd=repo_dir, check=True, capture_output=True)
    c_buggy = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True
    ).stdout.strip()

    # Post-fix commit C_fixed
    (repo_dir / "vuln.py").write_text("def bug():\n    return 'patched_secure'\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "fix security issue"], cwd=repo_dir, check=True, capture_output=True)

    # Dirty working tree modification
    (repo_dir / "vuln.py").write_text("def bug():\n    return 'dirty_working_tree'\n", encoding="utf-8")

    # Index strictly at c_buggy
    idx = RepositoryIndex(repo_dir=repo_dir, commit_hash=c_buggy)
    assert "vuln.py" in idx.files
    # Verify content matches c_buggy exactly, NOT c_fixed and NOT working tree
    assert "unpatched" in idx.files["vuln.py"]
    assert "patched_secure" not in idx.files["vuln.py"]
    assert "dirty_working_tree" not in idx.files["vuln.py"]


def test_target_chunk_exclusion_and_deduplication(mock_repo_index):
    """Verify target chunk is excluded and identical [path, start, end] excerpts are deduplicated."""
    from auditor.llm.context_retriever import RepositoryContextRetriever

    retriever = RepositoryContextRetriever(mock_repo_index)
    # Query calling check_token twice
    target_code = "from auth.helpers import check_token\ncheck_token('a')\ncheck_token('b')\n"

    section, items, omitted = retriever.retrieve_context(
        target_file="views/target.py",
        chunk_start=1,
        chunk_end=10,
        chunk_code=target_code,
        max_tokens=4000,
    )

    # Verify no item from active target file / chunk
    for item in items:
        assert item.file_path != "views/target.py"

    # Verify uniqueness of (file_path, start_line, end_line)
    keys = [(item.file_path, item.start_line, item.end_line) for item in items]
    assert len(keys) == len(set(keys)), "Duplicate context excerpts were not deduplicated"


def test_inv09_zero_leakage_on_stored_d_cases():
    """Verify that every stored Config D chunk prompt satisfies INV-09 zero answer-leakage."""
    import json

    from auditor.llm.prompt_builder import assert_zero_answer_leakage

    d_path = Path("data/results/config_d_pilot_run.json")
    if not d_path.exists():
        pytest.skip("config_d_pilot_run.json not found")

    with open(d_path, encoding="utf-8") as f:
        d_run = json.load(f)

    for case in d_run.get("cases", []):
        commit = case["commit_hash"]
        tf = case["target_file"]

        # Build forbidden terms
        forbidden = [commit[:8], tf.split("/")[-1].replace(".py", "") + "_fix"]
        for locus in case.get("gt_loci", []):
            if isinstance(locus, dict):
                did = locus.get("defect_id")
                sl = locus.get("start_line")
                el = locus.get("end_line")
                if did:
                    forbidden.append(did)
                if sl and el:
                    forbidden.append(f"lines {sl}-{el}")

        chunk_tel = case.get("telemetry", {}).get("chunk_telemetry", [])
        for ct in chunk_tel:
            prompt = ct.get("prompt_sent")
            if prompt:
                assert_zero_answer_leakage(prompt, forbidden_terms=forbidden)


def test_prompt_equivalence_config_c_and_d():
    """Verify Config D differs from Config C only by the neutral repository-context section."""
    from auditor.llm.chunker import SourceChunk
    from auditor.llm.prompt_builder import build_config_c_user_prompt, build_config_d_user_prompt

    chunk = SourceChunk(
        file_path="src/app.py",
        chunk_index=1,
        total_chunks=1,
        start_line=1,
        end_line=20,
        total_lines=20,
        rendered_text="=== AUDIT TARGET: src/app.py (Lines 1 to 20 of 20) ===\n1: x = 1\n=== END AUDIT TARGET ===",
        raw_code="x = 1\n",
        token_estimate=10,
        tier=1,
        scope_description="Test scope",
    )
    static_section = "### DETECTED STATIC ANALYSIS FINDINGS (FOR REFERENCE ONLY)\n- Finding 1"
    context_section = "### REPOSITORY CONTEXT EXCERPTS (FOR REFERENCE ONLY)\n- Excerpt 1"

    c_prompt = build_config_c_user_prompt(chunk, static_section=static_section)
    d_prompt = build_config_d_user_prompt(chunk, static_section=static_section, context_section=context_section)

    # When context_section is removed from d_prompt, it should match c_prompt structure
    assert "REPOSITORY CONTEXT EXCERPTS (FOR REFERENCE ONLY)" in d_prompt
    assert "REPOSITORY CONTEXT EXCERPTS (FOR REFERENCE ONLY)" not in c_prompt

    # Verify that d_prompt contains the exact c_prompt elements plus the context section
    assert (
        c_prompt.split("### DETECTED STATIC ANALYSIS FINDINGS")[0].strip()
        == d_prompt.split("### DETECTED STATIC ANALYSIS FINDINGS")[0].strip()
    )
    assert "### DETECTED STATIC ANALYSIS FINDINGS (FOR REFERENCE ONLY)" in d_prompt
    assert "- Finding 1" in d_prompt
    assert "### REPOSITORY CONTEXT EXCERPTS (FOR REFERENCE ONLY)" in d_prompt
    assert "- Excerpt 1" in d_prompt
    assert d_prompt.endswith(
        "Return your audit results exclusively as a valid JSON object matching the required schema."
    )


def test_context_budget_cap_enforcement(mock_repo_index):
    """Verify that context retrieval strictly caps output within max_tokens."""
    from auditor.llm.context_retriever import RepositoryContextRetriever

    retriever = RepositoryContextRetriever(mock_repo_index)
    target_code = "from auth.helpers import check_token\nfrom models.base import BaseModel\nclass MyView(BaseModel):\n    def handle(self):\n        check_token('foo')\n"

    # Very small budget: only 30 tokens
    section, items, omitted = retriever.retrieve_context(
        target_file="views/target.py",
        chunk_start=1,
        chunk_end=10,
        chunk_code=target_code,
        max_tokens=30,
    )

    # Should enforce cap: omitted items must be > 0 or 0 items accepted
    assert omitted > 0 or len(items) == 0
    if omitted > 0:
        assert "[Notice:" in section
