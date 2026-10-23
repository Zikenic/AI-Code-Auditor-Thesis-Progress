"""Unit and regression tests for Controlled Repository-Context Ablation Pilot."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from auditor.llm.chunker import SourceChunker
from auditor.llm.config import DEFAULT_CONFIG_D_PARAMS
from auditor.llm.context_retriever import RepositoryContextRetriever, RepositoryIndex
from auditor.llm.prompt_builder import build_config_d_user_prompt
from tools.run_context_ablation import ContextAblationHarness

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "data" / "ablation_manifest.json"


def test_ablation_manifest_structure_and_coverage():
    """Verify ablation manifest contains 6 distinct valid micro-repositories."""
    assert MANIFEST_PATH.exists()
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    fixtures = data.get("fixtures", [])
    assert len(fixtures) == 6

    expected_ids = {f"ABL-{i:04d}" for i in range(1, 7)}
    actual_ids = {f["fixture_id"] for f in fixtures}
    assert actual_ids == expected_ids

    for fix in fixtures:
        rdir = REPO_ROOT / fix["repo_dir"]
        assert rdir.exists() and rdir.is_dir()

        tfile = rdir / fix["target_file"]
        assert tfile.exists() and tfile.is_file()

        for hfile_name in fix["helper_files"]:
            hfile = rdir / hfile_name
            assert hfile.exists() and hfile.is_file()


@pytest.mark.parametrize("fixture_idx", range(6))
def test_retriever_scoping_and_symbol_extraction(fixture_idx: int):
    """Verify that retriever discovers exactly sibling modules and relevant helper symbols."""
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    fix = data["fixtures"][fixture_idx]

    rdir = REPO_ROOT / fix["repo_dir"]
    tfile = fix["target_file"]

    # Index strictly scoped to the fixture micro-repo
    repo_index = RepositoryIndex(repo_dir=rdir, commit_hash="clean")
    retriever = RepositoryContextRetriever(repo_index)

    # All discovered files must strictly belong to this fixture's directory
    for discovered in repo_index.files.keys():
        assert (rdir / discovered).exists()

    code = (rdir / tfile).read_text(encoding="utf-8")
    chunker = SourceChunker(token_budget=DEFAULT_CONFIG_D_PARAMS.source_token_budget)
    chunks = chunker.chunk_source(code, tfile)
    assert len(chunks) > 0
    chunk = chunks[0]

    context_section, used_tokens, hit_count = retriever.retrieve_context(
        target_file=tfile,
        chunk_start=chunk.start_line,
        chunk_end=chunk.end_line,
        chunk_code=chunk.raw_code,
        max_tokens=DEFAULT_CONFIG_D_PARAMS.context_token_budget,
    )

    # Must retrieve at least one relevant context item
    assert len(used_tokens) > 0
    assert len(context_section) > 0
    assert "### REPOSITORY CONTEXT EXCERPTS" in context_section

    # Target chunk itself must NEVER be in context
    for item in used_tokens:
        assert item.file_path != tfile or not (item.start_line == chunk.start_line and item.end_line == chunk.end_line)


def test_paired_prompt_exact_difference():
    """Verify that Arm N and Arm R prompts differ strictly by the context block insertion."""
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    fix = data["fixtures"][0]

    rdir = REPO_ROOT / fix["repo_dir"]
    tfile = fix["target_file"]

    repo_index = RepositoryIndex(repo_dir=rdir, commit_hash="clean")
    retriever = RepositoryContextRetriever(repo_index)

    code = (rdir / tfile).read_text(encoding="utf-8")
    chunker = SourceChunker(token_budget=DEFAULT_CONFIG_D_PARAMS.source_token_budget)
    chunk = chunker.chunk_source(code, tfile)[0]

    context_section, _, _ = retriever.retrieve_context(
        target_file=tfile,
        chunk_start=chunk.start_line,
        chunk_end=chunk.end_line,
        chunk_code=chunk.raw_code,
        max_tokens=DEFAULT_CONFIG_D_PARAMS.context_token_budget,
    )

    prompt_n = build_config_d_user_prompt(chunk, static_section="", context_section="")
    prompt_r = build_config_d_user_prompt(chunk, static_section="", context_section=context_section)

    assert "### REPOSITORY CONTEXT EXCERPTS" not in prompt_n
    assert "### REPOSITORY CONTEXT EXCERPTS" in prompt_r
    assert prompt_r.replace(f"\n\n{context_section}", "") == prompt_n


def test_offline_harness_execution(tmp_path: Path):
    """Verify that ContextAblationHarness executes cleanly offline and generates artifacts."""
    harness = ContextAblationHarness(
        manifest_path=MANIFEST_PATH,
        mode="offline",
        output_dir=tmp_path / "test_ablation_run",
    )

    artifacts = harness.execute_pilot(target_fixtures=["ABL-0001", "ABL-0002"])
    assert Path(artifacts["json"]).exists()
    assert Path(artifacts["csv"]).exists()
    assert Path(artifacts["md"]).exists()

    payload = json.loads(Path(artifacts["json"]).read_text(encoding="utf-8"))
    assert payload["metadata"]["total_slots"] == 4  # 2 fixtures x 2 arms
    assert len(payload["results"]) == 4

    results = payload["results"]
    arms = {r["arm"] for r in results}
    assert arms == {"N", "R"}
    for r in results:
        assert r["status"] == "success"
