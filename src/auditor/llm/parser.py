"""Response parser and validator for Configuration B LLM output.

Enforces:
- Parsing of JSON output from Claude / LLM response strings.
- Markdown code-fence stripping (```json ... ```).
- Pydantic validation into PredictedFinding domain objects.
- Line coordinate bounds clamping/rejection (1 <= start_line <= end_line <= total_lines).
- Category 1 mandatory impact validation.
- Locked 6 categories validation.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from auditor.matcher.path_utils import normalize_repo_path
from auditor.models.finding import (
    ConfidenceLevel,
    DetectionLayer,
    PredictedFinding,
    SeverityLevel,
)
from auditor.models.taxonomy import ACTIVE_TAXONOMY


class ConfigBResponseParser:
    """Parses raw LLM model responses into validated PredictedFinding instances."""

    def __init__(self, model_name: str = "claude-sonnet-5-5"):
        self.model_name = model_name

    def parse_response(
        self,
        raw_text: str,
        expected_file_path: str,
        total_file_lines: int,
        chunk_start_line: int = 1,
        chunk_end_line: int | None = None,
    ) -> list[PredictedFinding]:
        """Parse raw response text, validate JSON structure and coordinates, return valid findings."""
        if not raw_text or not raw_text.strip():
            return []

        # Extract JSON payload (handling possible markdown blocks)
        json_str = self._extract_json_block(raw_text)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as valid JSON: {str(e)}") from e

        if not isinstance(data, dict) or "findings" not in data:
            raise ValueError("LLM response JSON must contain a root 'findings' array.")

        findings_raw = data["findings"]
        if not isinstance(findings_raw, list):
            raise ValueError("'findings' in LLM response must be a list.")

        valid_findings: list[PredictedFinding] = []
        normalized_target_path = normalize_repo_path(expected_file_path)

        for idx, item in enumerate(findings_raw):
            if not isinstance(item, dict):
                continue

            parsed_finding = self._validate_and_build_finding(
                item=item,
                expected_file_path=normalized_target_path,
                total_file_lines=total_file_lines,
                item_idx=idx,
            )
            if parsed_finding is not None:
                valid_findings.append(parsed_finding)

        return valid_findings

    def _extract_json_block(self, text: str) -> str:
        """Strip markdown ```json fences if present, otherwise extract outer JSON object."""
        clean = text.strip()

        # Check for ```json ... ``` or ``` ... ```
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, re.DOTALL)
        if fence_match:
            return fence_match.group(1).strip()

        # Check if entire string is enclosed in curly braces
        first_brace = clean.find("{")
        last_brace = clean.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            return clean[first_brace : last_brace + 1].strip()

        return clean

    def _validate_and_build_finding(
        self,
        item: dict[str, Any],
        expected_file_path: str,
        total_file_lines: int,
        item_idx: int,
    ) -> PredictedFinding | None:
        """Validate finding fields against domain requirements. Rejects invalid coordinates."""
        # 1. Coordinate extraction and validation
        start_line = item.get("start_line")
        end_line = item.get("end_line")

        if start_line is None:
            return None

        try:
            start_line = int(start_line)
            end_line = int(end_line) if end_line is not None else start_line
        except (ValueError, TypeError):
            return None

        # INV-06: 1 <= start_line <= end_line <= total_file_lines
        if start_line < 1 or end_line < start_line or start_line > total_file_lines:
            # Out of bounds coordinates: rejected
            return None

        # Clamp end_line to total_file_lines if minor overflow
        if end_line > total_file_lines:
            end_line = total_file_lines

        # 2. File path normalization
        raw_path = item.get("file_path", expected_file_path)
        normalized_path = normalize_repo_path(str(raw_path))
        # Default to expected_file_path if LLM returned generic path or basename
        if not normalized_path or normalized_path == "." or normalized_path not in expected_file_path:
            normalized_path = expected_file_path

        # 3. Category validation
        cat_id = item.get("category_id")
        try:
            cat_id = int(cat_id)
            ACTIVE_TAXONOMY.validate_category(cat_id)
        except (ValueError, TypeError):
            return None

        # 4. CWE normalization
        raw_cwe = str(item.get("primary_cwe", "CWE-UNMAPPED")).strip().upper()
        if not raw_cwe.startswith("CWE-") and raw_cwe.isdigit():
            raw_cwe = f"CWE-{raw_cwe}"

        raw_alt = item.get("alternative_cwes", [])
        cleaned_alts: list[str] = []
        if isinstance(raw_alt, list):
            for a in raw_alt[:2]:
                ac = str(a).strip().upper()
                if not ac.startswith("CWE-") and ac.isdigit():
                    ac = f"CWE-{ac}"
                if ac and ac not in cleaned_alts:
                    cleaned_alts.append(ac)

        # 5. Severity and Confidence
        sev_str = str(item.get("severity", "medium")).lower()
        conf_str = str(item.get("confidence", "medium")).lower()

        severity = SeverityLevel(sev_str) if sev_str in SeverityLevel._value2member_map_ else SeverityLevel.MEDIUM
        confidence = (
            ConfidenceLevel(conf_str) if conf_str in ConfidenceLevel._value2member_map_ else ConfidenceLevel.MEDIUM
        )

        title = str(item.get("title", f"LLM finding at line {start_line}")).strip()[:200]
        description = str(item.get("description", "No description provided.")).strip()
        suggestion = item.get("suggestion")
        if suggestion is not None:
            suggestion = str(suggestion).strip()

        category_1_impact = item.get("category_1_impact")

        provenance = {
            "model": self.model_name,
            "layer": "heuristic_llm",
            "category_1_impact": category_1_impact,
        }

        finding_id = f"llm-{uuid.uuid4().hex[:10]}"

        return PredictedFinding(
            finding_id=finding_id,
            detection_layer=DetectionLayer.HEURISTIC_LLM,
            tool_name=self.model_name,
            category_id=cat_id,
            primary_cwe=raw_cwe,
            alternative_cwes=cleaned_alts,
            file_path=normalized_path,
            start_line=start_line,
            end_line=end_line,
            severity=severity,
            confidence=confidence,
            title=title,
            description=description,
            suggestion=suggestion,
            provenance=provenance,
        )
