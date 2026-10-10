"""Deterministic static-analysis engine implementing IStaticAnalysisEngine.

Executes pinned Ruff and Semgrep Community Edition runners against controlled
source copies with repository-controlled suppression isolation.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from auditor.models.finding import PredictedFinding
from auditor.orchestration.interfaces import IStaticAnalysisEngine
from auditor.static_analysis import (
    RULESET_MANIFEST_PATH,
    SEMGREP_RULES_PATH,
)
from auditor.static_analysis.mapper import FindingMapper
from auditor.static_analysis.suppression import ControlledSourceWorkspace

logger = logging.getLogger(__name__)


def deduplicate_static_findings(findings: list[PredictedFinding]) -> list[PredictedFinding]:
    """Deduplicate static findings on identical file, overlapping locus, and matching CWE."""
    if len(findings) <= 1:
        return findings

    deduped: list[PredictedFinding] = []
    for f in findings:
        matched = False
        for existing in deduped:
            if (
                existing.file_path == f.file_path
                and existing.category_id == f.category_id
                and existing.primary_cwe == f.primary_cwe
            ):
                # Check line overlap or proximity within +-2 lines
                if (
                    existing.start_line is not None
                    and existing.end_line is not None
                    and f.start_line is not None
                    and f.end_line is not None
                ):
                    overlap = max(0, min(existing.end_line, f.end_line) - max(existing.start_line, f.start_line) + 1)
                    proximity = abs(existing.start_line - f.start_line) <= 2
                    if overlap > 0 or proximity:
                        # Merge provenance
                        existing_tools = existing.provenance.get("tools", [existing.tool_name])
                        if f.tool_name not in existing_tools:
                            existing_tools.append(f.tool_name)
                        existing.provenance["tools"] = existing_tools
                        matched = True
                        break
        if not matched:
            deduped.append(f)

    return deduped


class StaticAnalysisEngine(IStaticAnalysisEngine):
    """Executes deterministic static analysis (Ruff and Semgrep CE) under frozen ruleset and suppression isolation."""

    def __init__(
        self,
        manifest_path: Path | str | None = None,
        semgrep_rules_path: Path | str | None = None,
        timeout_seconds: int = 60,
    ):
        self.manifest_path = Path(manifest_path) if manifest_path else RULESET_MANIFEST_PATH
        self.semgrep_rules_path = Path(semgrep_rules_path) if semgrep_rules_path else SEMGREP_RULES_PATH
        self.timeout_seconds = timeout_seconds
        self.mapper = FindingMapper(self.manifest_path)

    def run_static_analysis(
        self,
        workspace_path: str | None,
        changed_files: list[str],
    ) -> list[PredictedFinding]:
        """Run deterministic static checks and emit normalized findings."""
        # 1. Filter changed files to Python source files only
        py_files = [f for f in changed_files if f.endswith(".py")]
        if not py_files:
            return []

        base_path = Path(workspace_path) if workspace_path else Path.cwd()
        raw_findings: list[PredictedFinding] = []

        # 2. Execute under ControlledSourceWorkspace (suppression isolation)
        with ControlledSourceWorkspace(base_path, py_files) as controlled_ws:
            if not controlled_ws.copied_files:
                return []

            # Map from isolated absolute path to original relative repository path
            path_mapping: dict[str, str] = {}
            for copied in controlled_ws.copied_files:
                # relative to isolated_root
                rel_path = str(copied.relative_to(controlled_ws.isolated_root)).replace("\\", "/")
                path_mapping[str(copied.resolve())] = rel_path
                # Also store lowercase / forward-slash variations for robust matching on Windows
                path_mapping[str(copied).lower()] = rel_path
                path_mapping[str(copied).replace("\\", "/").lower()] = rel_path

            # 3. Execute Ruff Runner
            ruff_findings = self._run_ruff(controlled_ws.copied_files, path_mapping)
            raw_findings.extend(ruff_findings)

            # 4. Execute Semgrep Runner
            semgrep_findings = self._run_semgrep(controlled_ws.copied_files, path_mapping)
            raw_findings.extend(semgrep_findings)

        # 5. Deduplicate and return
        return deduplicate_static_findings(raw_findings)

    def _run_ruff(
        self,
        target_files: list[Path],
        path_mapping: dict[str, str],
    ) -> list[PredictedFinding]:
        """Execute pinned Ruff CLI in isolated mode."""
        cmd = [
            "uv",
            "run",
            "ruff",
            "check",
            "--isolated",
            "--ignore-noqa",
            "--no-respect-gitignore",
            "--no-cache",
            "--select",
            "S,B,F601,F602,F631,F632,F634",
            "--output-format",
            "json",
        ] + [str(p) for p in target_files]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Ruff static analysis timed out after %ds", self.timeout_seconds)
            return []
        except Exception as e:
            logger.error("Ruff execution error: %s", e)
            return []

        # Ruff exits with code 1 when lint violations are found; exit code 0 when clean.
        if not res.stdout.strip():
            return []

        try:
            items = json.loads(res.stdout)
        except json.JSONDecodeError:
            logger.error("Failed to parse Ruff JSON output: %s", res.stdout[:200])
            return []

        findings: list[PredictedFinding] = []
        for item in items:
            raw_filename = str(item.get("filename") or "")
            rel_file = self._resolve_relative_path(raw_filename, path_mapping)
            try:
                finding = self.mapper.map_ruff_finding(item, rel_file)
                findings.append(finding)
            except Exception as e:
                logger.warning("Error mapping Ruff finding: %s", e)

        return findings

    def _run_semgrep(
        self,
        target_files: list[Path],
        path_mapping: dict[str, str],
    ) -> list[PredictedFinding]:
        """Execute pinned Semgrep CE CLI in isolated mode."""
        if not self.semgrep_rules_path.exists():
            logger.error("Semgrep rules file not found: %s", self.semgrep_rules_path)
            return []

        cmd = [
            "uv",
            "run",
            "semgrep",
            "scan",
            "--config",
            str(self.semgrep_rules_path),
            "--disable-version-check",
            "--metrics=off",
            "--no-git-ignore",
            "--json",
        ] + [str(p) for p in target_files]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Semgrep static analysis timed out after %ds", self.timeout_seconds)
            return []
        except Exception as e:
            logger.error("Semgrep execution error: %s", e)
            return []

        if not res.stdout.strip():
            return []

        try:
            data = json.loads(res.stdout)
        except json.JSONDecodeError:
            logger.error("Failed to parse Semgrep JSON output: %s", res.stdout[:200])
            return []

        results = data.get("results", [])
        findings: list[PredictedFinding] = []
        for item in results:
            raw_path = str(item.get("path") or "")
            rel_file = self._resolve_relative_path(raw_path, path_mapping)
            try:
                finding = self.mapper.map_semgrep_finding(item, rel_file)
                findings.append(finding)
            except Exception as e:
                logger.warning("Error mapping Semgrep finding: %s", e)

        return findings

    def _resolve_relative_path(self, raw_path: str, path_mapping: dict[str, str]) -> str:
        """Resolve raw file path from tool output back to original repository-relative path."""
        # 1. Exact match in path mapping
        if raw_path in path_mapping:
            return path_mapping[raw_path]

        resolved_str = str(Path(raw_path).resolve())
        if resolved_str in path_mapping:
            return path_mapping[resolved_str]

        lower_key = raw_path.lower()
        if lower_key in path_mapping:
            return path_mapping[lower_key]

        normalized_forward = raw_path.replace("\\", "/").lower()
        for k, v in path_mapping.items():
            if k in normalized_forward or normalized_forward.endswith(v.lower()):
                return v

        # Fallback: clean path basename or relative
        return Path(raw_path).name
