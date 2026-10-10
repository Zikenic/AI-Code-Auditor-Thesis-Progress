#!/usr/bin/env python3
"""Minimal Local Repository Demonstration Script for AI Code Auditor (Week 3–4 Closeout).

Executes the existing deterministic static analysis engine (Ruff v0.16.10 + Semgrep CE v1.180.0)
over a designated local workspace or file path using offline-isolated execution.

Licensing & Offline Safeguards:
- Does NOT invoke hosted LLMs, external APIs, cloud registries, or remote services.
- Does NOT transmit code, findings, or rule text over the network.
- Invokes Ruff and Semgrep exclusively via local pinned CLI binaries with telemetry disabled.
- Operates strictly offline.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from auditor.models.finding import PredictedFinding
from auditor.static_analysis.engine import StaticAnalysisEngine


def discover_python_files(target: Path) -> list[str]:
    """Discover Python source files relative to target workspace root or single file."""
    if target.is_file():
        if target.suffix == ".py":
            return [target.name]
        return []

    py_files: list[str] = []
    for p in target.rglob("*.py"):
        # Exclude common virtualenv and cache directories
        parts = set(p.parts)
        if any(ignored in parts for ignored in (".venv", "venv", ".git", "__pycache__", ".pytest_cache", ".ruff_cache")):
            continue
        try:
            rel = p.relative_to(target).as_posix()
            py_files.append(rel)
        except ValueError:
            continue

    return sorted(py_files)


def format_finding_card(finding: PredictedFinding, index: int) -> str:
    """Format a single finding into a readable terminal card."""
    lines_str = (
        f"{finding.start_line}-{finding.end_line}"
        if finding.start_line != finding.end_line
        else f"{finding.start_line}"
    ) if finding.start_line is not None else "N/A"

    tool_rule = finding.provenance.get("rule_code") or finding.provenance.get("rule_id") or finding.tool_name
    category_label = f"Category {finding.category_id}"

    card = [
        f"[{index:02d}] {finding.title}",
        f"     File:        {finding.file_path}:{lines_str}",
        f"     Tool/Rule:   {finding.tool_name.upper()} | {tool_rule}",
        f"     Taxonomy:    {category_label} ({finding.primary_cwe})",
        f"     Severity:    {finding.severity.upper()} | Confidence: {finding.confidence.upper()}",
        f"     Description: {finding.description}",
    ]
    if finding.suggestion:
        card.append(f"     Suggestion:  {finding.suggestion}")

    return "\n".join(card)


def run_demo(
    target_path: Path,
    engine: StaticAnalysisEngine | None = None,
) -> tuple[int, list[PredictedFinding]]:
    """Execute local static analysis demonstration on target_path.

    Returns:
        (exit_code, findings_list)
    """
    resolved_path = target_path.resolve()
    if not resolved_path.exists():
        print(f"Error: Target path does not exist: {target_path}", file=sys.stderr)
        return 1, []

    if resolved_path.is_file():
        workspace_dir = resolved_path.parent
        files_to_analyze = [resolved_path.name]
    else:
        workspace_dir = resolved_path
        files_to_analyze = discover_python_files(workspace_dir)

    print("================================================================================")
    print("AI CODE AUDITOR — LOCAL REPOSITORY DEMONSTRATION")
    print(f"Target:    {resolved_path}")
    print(f"Workspace: {workspace_dir}")
    print(f"Files:     {len(files_to_analyze)} Python source file(s) discovered")
    print("Mode:      Offline Static Analysis (Ruff + Semgrep CE, Suppression Isolated)")
    print("================================================================================\n")

    if not files_to_analyze:
        print("No Python (.py) source files found in target. Analysis skipped.")
        return 0, []

    if engine is None:
        try:
            engine = StaticAnalysisEngine()
        except Exception as e:
            print(f"Error initializing StaticAnalysisEngine: {e}", file=sys.stderr)
            return 2, []

    try:
        findings = engine.run_static_analysis(
            workspace_path=str(workspace_dir),
            changed_files=files_to_analyze,
        )
    except Exception as e:
        print(f"Analysis failure: {e}", file=sys.stderr)
        return 2, []

    print(f"Analysis completed successfully. Emitted {len(findings)} finding(s).\n")

    if not findings:
        print("[OK] Zero findings detected. All inspected files clean under frozen static rules.")
        return 0, []

    for idx, f in enumerate(findings, 1):
        print(format_finding_card(f, idx))
        print("-" * 80)

    return 0, findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run local offline repository static-analysis demonstration.",
    )
    parser.add_argument(
        "target",
        type=str,
        help="Path to local repository directory or Python file to analyze.",
    )
    args = parser.parse_args(argv)

    code, _ = run_demo(Path(args.target))
    return code


if __name__ == "__main__":
    sys.exit(main())
