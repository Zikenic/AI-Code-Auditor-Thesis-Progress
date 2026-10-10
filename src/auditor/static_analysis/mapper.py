"""Normalization and mapping of raw static-analysis outputs into domain models.

Loads the frozen ruleset manifest (ruleset_manifest.json) and converts raw Ruff and Semgrep
JSON payloads into standardized PredictedFinding objects under the locked 6-category taxonomy.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from auditor.models.finding import (
    ConfidenceLevel,
    DetectionLayer,
    PredictedFinding,
    SeverityLevel,
)
from auditor.static_analysis import RULESET_MANIFEST_PATH


class FindingMapper:
    """Normalizes raw CLI output findings into PredictedFinding domain objects."""

    def __init__(self, manifest_path: Path | str | None = None):
        self.manifest_path = Path(manifest_path) if manifest_path else RULESET_MANIFEST_PATH
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Ruleset manifest not found at: {self.manifest_path}")

        manifest_data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.manifest = manifest_data
        self.rule_mappings: dict[str, dict[str, Any]] = manifest_data.get("rule_mappings", {})
        self.unmapped_policy: dict[str, Any] = manifest_data.get("unmapped_prediction_policy", {})

    def _resolve_rule_mapping(self, tool: str, rule_id: str) -> dict[str, Any]:
        """Resolve a rule mapping from the manifest, falling back to unmapped policy."""
        # 1. Exact key lookup
        direct_key = f"{tool}.{rule_id}"
        if direct_key in self.rule_mappings:
            return self.rule_mappings[direct_key]

        # 2. Suffix match (e.g. for semgrep check_id prefixed with file path)
        prefix = f"{tool}."
        for key, mapping in self.rule_mappings.items():
            if key.startswith(prefix):
                short_rule_id = key[len(prefix) :]
                if rule_id.endswith(short_rule_id):
                    return mapping

        # 3. Fallback to unmapped policy
        return {
            "tool": tool,
            "rule_id": rule_id,
            "category_id": self.unmapped_policy.get("fallback_category_id", 1),
            "primary_cwe": self.unmapped_policy.get("fallback_primary_cwe", "CWE-UNMAPPED"),
            "alternative_cwes": self.unmapped_policy.get("fallback_alternative_cwes", []),
            "description": f"Unmapped rule: {rule_id}",
            "is_unmapped": True,
        }

    def map_ruff_finding(
        self,
        raw_finding: dict[str, Any],
        relative_file_path: str,
    ) -> PredictedFinding:
        """Map a single raw Ruff JSON finding into a PredictedFinding."""
        code = str(raw_finding.get("code") or "UNKNOWN")
        mapping = self._resolve_rule_mapping("ruff", code)

        start_loc = raw_finding.get("location") or {}
        end_loc = raw_finding.get("end_location") or {}
        start_line = start_loc.get("row")
        end_line = end_loc.get("row") or start_line

        finding_id = f"static-ruff-{uuid.uuid4().hex[:10]}"
        message = raw_finding.get("message", "Static check violation detected by Ruff")

        return PredictedFinding(
            finding_id=finding_id,
            detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
            tool_name="ruff",
            category_id=mapping["category_id"],
            primary_cwe=mapping["primary_cwe"],
            alternative_cwes=mapping.get("alternative_cwes", []),
            file_path=relative_file_path,
            start_line=start_line,
            end_line=end_line,
            severity=SeverityLevel.MEDIUM,
            confidence=ConfidenceLevel.HIGH,
            title=f"Ruff [{code}]: {mapping.get('description', message)}",
            description=message,
            provenance={
                "tool": "ruff",
                "rule_code": code,
                "url": raw_finding.get("url"),
                "is_unmapped": mapping.get("is_unmapped", False),
            },
        )

    def map_semgrep_finding(
        self,
        raw_finding: dict[str, Any],
        relative_file_path: str,
    ) -> PredictedFinding:
        """Map a single raw Semgrep JSON finding into a PredictedFinding."""
        check_id = str(raw_finding.get("check_id") or "UNKNOWN")
        mapping = self._resolve_rule_mapping("semgrep", check_id)

        start = raw_finding.get("start") or {}
        end = raw_finding.get("end") or {}
        start_line = start.get("line")
        end_line = end.get("line") or start_line

        extra = raw_finding.get("extra") or {}
        raw_sev = str(extra.get("severity") or "WARNING").upper()
        if raw_sev == "ERROR":
            severity = SeverityLevel.HIGH
        elif raw_sev == "INFO":
            severity = SeverityLevel.LOW
        else:
            severity = SeverityLevel.MEDIUM

        message = str(extra.get("message") or "Security finding detected by Semgrep").strip()
        first_line_msg = message.split("\n")[0] if message else check_id

        finding_id = f"static-semgrep-{uuid.uuid4().hex[:10]}"

        return PredictedFinding(
            finding_id=finding_id,
            detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
            tool_name="semgrep",
            category_id=mapping["category_id"],
            primary_cwe=mapping["primary_cwe"],
            alternative_cwes=mapping.get("alternative_cwes", []),
            file_path=relative_file_path,
            start_line=start_line,
            end_line=end_line,
            severity=severity,
            confidence=ConfidenceLevel.HIGH,
            title=f"Semgrep [{mapping.get('rule_id', check_id)}]: {first_line_msg[:120]}",
            description=message,
            provenance={
                "tool": "semgrep",
                "check_id": check_id,
                "metadata": extra.get("metadata", {}),
                "is_unmapped": mapping.get("is_unmapped", False),
            },
        )
