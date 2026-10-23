"""Predicted finding models and detection layers."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from auditor.models.taxonomy import ACTIVE_TAXONOMY


class DetectionLayer(StrEnum):
    """The detection layer responsible for emitting the finding."""

    DETERMINISTIC_STATIC = "deterministic_static"
    HEURISTIC_LLM = "heuristic_llm"


class SeverityLevel(StrEnum):
    """Severity classification for audit findings."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfidenceLevel(StrEnum):
    """Confidence assessment for audit findings."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TriageStatus(StrEnum):
    """Triage verdict assigned by LLM review in hybrid configurations."""

    CONFIRMED = "confirmed"
    LIKELY_FALSE_POSITIVE = "likely_false_positive"
    INCONCLUSIVE = "inconclusive"


class PredictedFinding(BaseModel):
    """Normalized finding emitted by the static or LLM auditing engines."""

    finding_id: str = Field(..., description="Unique finding UUID or hash.")
    detection_layer: DetectionLayer = Field(..., description="Deterministic static or heuristic LLM.")
    tool_name: str = Field(..., description="Tool or model identifier (e.g., 'ruff', 'semgrep', 'gemini-1.5-pro').")
    category_id: int = Field(..., description="Taxonomy category ID (1..6 default, up to 8 if approved).")
    primary_cwe: str = Field(..., description="Primary CWE identifier (e.g., 'CWE-89').")
    alternative_cwes: list[str] = Field(
        default_factory=list,
        description="Up to 2 additional alternative CWE labels (max 3 total labels).",
    )
    file_path: str = Field(..., description="Repository-relative target file path.")
    start_line: int | None = Field(default=None, description="1-indexed starting line number.")
    end_line: int | None = Field(default=None, description="1-indexed ending line number.")
    severity: SeverityLevel = Field(default=SeverityLevel.MEDIUM, description="Finding severity.")
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.MEDIUM, description="Finding confidence.")
    title: str = Field(..., description="Short summary title.")
    description: str = Field(..., description="Detailed explanation of the defect.")
    suggestion: str | None = Field(default=None, description="Remediation suggestion.")
    provenance: dict[str, Any] = Field(default_factory=dict, description="Metadata trace (rules, prompts, tokens).")

    @field_validator("primary_cwe")
    @classmethod
    def normalize_primary_cwe(cls, v: str) -> str:
        clean = v.strip().upper()
        if not clean.startswith("CWE-") and clean.isdigit():
            clean = f"CWE-{clean}"
        return clean

    @field_validator("alternative_cwes")
    @classmethod
    def normalize_alternative_cwes(cls, v: list[str]) -> list[str]:
        cleaned = []
        for item in v:
            c = item.strip().upper()
            if not c.startswith("CWE-") and c.isdigit():
                c = f"CWE-{c}"
            if c not in cleaned:
                cleaned.append(c)
        if len(cleaned) > 2:
            raise ValueError(f"Methodology limits cases to at most 2 alternative CWEs (received {len(cleaned)}).")
        return cleaned

    @field_validator("category_id")
    @classmethod
    def validate_category(cls, v: int) -> int:
        return ACTIVE_TAXONOMY.validate_category(v)

    @model_validator(mode="after")
    def validate_line_coordinates(self) -> "PredictedFinding":
        if self.start_line is not None and self.end_line is None:
            self.end_line = self.start_line
        if self.start_line is not None and self.end_line is not None:
            if self.start_line < 1:
                raise ValueError(f"start_line must be >= 1 (got {self.start_line}).")
            if self.end_line < self.start_line:
                raise ValueError(f"end_line ({self.end_line}) cannot be less than start_line ({self.start_line}).")
        return self

    def has_line_coordinates(self) -> bool:
        """Return True if the finding has usable positive line coordinates."""
        return self.start_line is not None and self.end_line is not None and self.start_line >= 1

    def is_confirmed(self) -> bool:
        """Check if finding was confirmed by LLM triage."""
        return self.provenance.get("triage") == TriageStatus.CONFIRMED.value

    def is_likely_false_positive(self) -> bool:
        """Check if finding was marked as a likely false positive by LLM triage."""
        return self.provenance.get("triage") == TriageStatus.LIKELY_FALSE_POSITIVE.value

    def is_inconclusive(self) -> bool:
        """Check if finding triage was deemed inconclusive by LLM review."""
        return self.provenance.get("triage") == TriageStatus.INCONCLUSIVE.value

    def apply_triage(
        self,
        triage: TriageStatus | str,
        rationale: str,
        triaged_by: str = "llm",
        refined_title: str | None = None,
        refined_description: str | None = None,
    ) -> None:
        """Enrich finding provenance with LLM triage decision without discarding static evidence."""
        triage_str = triage.value if isinstance(triage, TriageStatus) else str(triage).lower()
        self.provenance["triage"] = triage_str
        self.provenance["triage_rationale"] = rationale
        self.provenance["triaged_by"] = triaged_by
        if refined_title:
            self.provenance["refined_title"] = refined_title
        if refined_description:
            self.provenance["refined_description"] = refined_description
