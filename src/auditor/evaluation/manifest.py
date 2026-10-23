"""Benchmark Manifest schema, loader, and validation contracts.

Provides:
- Machine-readable benchmark manifest specification adhering to project conventions.
- Distinction between verified defective cases, verified clean cases, and unknown expectation cases.
- Safe loading and normalization of benchmark cases from data/pilot_cases.json or custom manifests.
- Exclusions of unannotated or unknown cases from ground-truth metric denominators.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from auditor.models.ground_truth import BenchmarkCase, GroundTruthDefect, ImpactType


class AnnotationState(StrEnum):
    """Ground-truth annotation confidence state."""

    VERIFIED = "verified"  # Verified defective case with annotated defects
    CLEAN = "clean"  # Verified clean case with zero defects
    UNKNOWN = "unknown"  # Unannotated, speculative, or pending human adjudication


class AnnotationCompleteness(StrEnum):
    """Ground-truth annotation scope completeness within evaluated file."""

    EXHAUSTIVE = "exhaustive"  # All known target-category defects in defined scope reviewed & annotated
    PARTIAL = "partial"  # Only specific defect locus annotated; negative space unadjudicated
    UNKNOWN = "unknown"  # Annotation completeness has not been established


class ManifestCase(BaseModel):
    """Single benchmark evaluation test case in the manifest contract."""

    case_id: str = Field(..., description="Stable case identifier (e.g., 'CAND-0001', 'CTRL-0001').")
    paired_case_id: str | None = Field(default=None, description="Paired defective case ID for clean controls.")
    repository: str = Field(..., description="Repository full name (e.g., 'tornadoweb/tornado').")
    commit_hash: str = Field(..., description="Target git commit SHA or fixture revision.")
    buggy_commit: str | None = Field(default=None, description="Pre-fix buggy commit SHA.")
    fixed_commit: str | None = Field(default=None, description="Post-fix commit SHA.")
    target_file: str = Field(..., description="Repository-relative target file path or fixture file name.")
    fixture_path: str | None = Field(default=None, description="Local fixture path relative to repo root.")
    language: str = Field(default="python", description="Programming language of target file.")
    is_buggy: bool = Field(..., description="True if case is defective; False if clean.")
    annotation_state: AnnotationState = Field(
        default=AnnotationState.VERIFIED,
        description="Annotation verification state: verified, clean, or unknown.",
    )
    annotation_completeness: AnnotationCompleteness = Field(
        default=AnnotationCompleteness.PARTIAL,
        description="Annotation completeness: exhaustive, partial, or unknown.",
    )
    category_id: int | None = Field(default=None, description="Primary taxonomy category ID (1..6).")
    reviewed_categories: list[int] = Field(default_factory=list, description="Categories audited during review.")
    target_scope: str | None = Field(default=None, description="Declared scope definition of reviewed code.")
    intended_behavior: str | None = Field(default=None, description="Intended safe design behavior.")
    validation_notes: str | None = Field(default=None, description="Verification rationale, test commands, or notes.")
    primary_cwe: str | None = Field(default=None, description="Primary CWE identifier (e.g., 'CWE-89').")
    acceptable_alternative_cwes: list[str] = Field(default_factory=list, description="Alternative CWEs.")
    line_ranges: list[list[int]] = Field(default_factory=list, description="Ground-truth line ranges [[s, e]].")
    defects: list[dict[str, Any]] = Field(default_factory=list, description="List of defect annotations.")
    reproducer: str | None = Field(default=None, description="Reproduction command or citation.")
    reproducer_status: str = Field(default="not_attempted", description="Reproduction execution status.")
    source_reference: str | None = Field(default=None, description="Originating document, advisory, or commit URL.")
    contextual_files: list[str] = Field(default_factory=list, description="Associated contextual files.")
    synthetic: bool = Field(default=False, description="True if fixture was synthetically constructed for evaluation.")
    source_type: str | None = Field(
        default=None,
        description="Explicit source origin type: 'upstream_repository_snapshot', 'handcrafted_clean_fixture', 'synthetic_fixture'.",
    )
    provenance: dict[str, Any] = Field(default_factory=dict, description="Provenance metadata.")

    @model_validator(mode="after")
    def validate_annotation_consistency(self) -> ManifestCase:
        if self.is_buggy and self.annotation_state == AnnotationState.CLEAN:
            raise ValueError(f"Case '{self.case_id}' cannot have is_buggy=True and annotation_state=CLEAN.")
        if not self.is_buggy and self.annotation_state == AnnotationState.VERIFIED:
            self.annotation_state = AnnotationState.CLEAN
        if self.annotation_state == AnnotationState.VERIFIED and len(self.defects) == 0:
            # If line_ranges and category_id are present, construct defect record
            if self.category_id is not None and self.primary_cwe and self.line_ranges:
                for idx, lr in enumerate(self.line_ranges, start=1):
                    self.defects.append(
                        {
                            "defect_id": f"{self.case_id}-DEF-{idx}",
                            "category_id": self.category_id,
                            "impact": "functional" if self.category_id == 1 else None,
                            "primary_cwe": self.primary_cwe,
                            "acceptable_alternative_cwes": self.acceptable_alternative_cwes,
                            "file_path": self.target_file,
                            "start_line": lr[0],
                            "end_line": lr[1] if len(lr) > 1 else lr[0],
                            "description": f"Ground-truth locus {lr[0]}-{lr[1] if len(lr) > 1 else lr[0]}",
                        }
                    )
        return self

    def to_benchmark_case(self) -> BenchmarkCase:
        """Convert manifest case into domain BenchmarkCase object for matcher evaluation."""
        if self.annotation_state == AnnotationState.CLEAN:
            return BenchmarkCase(
                case_id=self.case_id,
                repository=self.repository,
                commit_hash=self.commit_hash,
                is_buggy=False,
                verification_status="CLEAN_VERIFIED",
                annotation_completeness=self.annotation_completeness.value,
                contextual_files=self.contextual_files,
                defects=[],
            )

        parsed_defects: list[GroundTruthDefect] = []
        for d in self.defects:
            impact_val = None
            if d.get("category_id") == 1:
                imp = str(d.get("impact", "functional")).lower()
                impact_val = ImpactType.SECURITY if imp == "security" else ImpactType.FUNCTIONAL

            parsed_defects.append(
                GroundTruthDefect(
                    defect_id=d["defect_id"],
                    category_id=d["category_id"],
                    impact=impact_val,
                    primary_cwe=d["primary_cwe"],
                    acceptable_alternative_cwes=set(d.get("acceptable_alternative_cwes") or []),
                    file_path=d.get("file_path") or self.target_file,
                    start_line=d["start_line"],
                    end_line=d["end_line"],
                    description=d.get("description"),
                )
            )

        status_str = (
            "GROUND_TRUTH_VERIFIED"
            if self.annotation_state == AnnotationState.VERIFIED
            else "PENDING_VERIFICATION"
        )
        return BenchmarkCase(
            case_id=self.case_id,
            repository=self.repository,
            commit_hash=self.commit_hash,
            is_buggy=self.is_buggy,
            verification_status=status_str,
            annotation_completeness=self.annotation_completeness.value,
            contextual_files=self.contextual_files,
            defects=parsed_defects,
        )


class BenchmarkManifest(BaseModel):
    """Complete machine-readable benchmark manifest containing all evaluation cases."""

    manifest_version: str = Field(default="1.1.0", description="Manifest contract version.")
    description: str = Field(..., description="Manifest documentation and dataset scope.")
    cases: list[ManifestCase] = Field(default_factory=list, description="List of benchmark test cases.")

    def get_verified_buggy_cases(self) -> list[ManifestCase]:
        """Return cases that have verified ground-truth defects."""
        return [c for c in self.cases if c.is_buggy and c.annotation_state == AnnotationState.VERIFIED]

    def get_clean_cases(self) -> list[ManifestCase]:
        """Return cases that are verified clean (non-defective)."""
        return [c for c in self.cases if not c.is_buggy or c.annotation_state == AnnotationState.CLEAN]

    def get_exhaustive_cases(self) -> list[ManifestCase]:
        """Return cases that have exhaustive annotation completeness."""
        return [c for c in self.cases if c.annotation_completeness == AnnotationCompleteness.EXHAUSTIVE]

    def get_partial_cases(self) -> list[ManifestCase]:
        """Return cases that have partial annotation completeness."""
        return [c for c in self.cases if c.annotation_completeness == AnnotationCompleteness.PARTIAL]

    def get_unknown_cases(self) -> list[ManifestCase]:
        """Return cases whose defect status or annotations are unknown/pending."""
        return [
            c
            for c in self.cases
            if c.annotation_state == AnnotationState.UNKNOWN
            or c.annotation_completeness == AnnotationCompleteness.UNKNOWN
        ]

    def get_case(self, case_id: str) -> ManifestCase | None:
        """Find a single case by case_id."""
        for c in self.cases:
            if c.case_id.upper() == case_id.upper():
                return c
        return None


def load_benchmark_manifest(manifest_path: Path | None = None) -> BenchmarkManifest:
    """Load benchmark manifest from benchmark_manifest.json, pilot_cases.json, or custom path."""
    repo_root = Path(__file__).resolve().parents[3]
    if manifest_path:
        path = manifest_path
    else:
        candidate_unified = repo_root / "data" / "benchmark_manifest.json"
        path = candidate_unified if candidate_unified.exists() else (repo_root / "data" / "pilot_cases.json")

    if not path.exists():
        raise FileNotFoundError(f"Benchmark manifest file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    raw_cases = data.get("cases", [])
    parsed_cases: list[ManifestCase] = []

    for item in raw_cases:
        # Normalize fields from data/pilot_cases.json
        provenance = item.get("provenance") or {}
        src_ref = provenance.get("source_doc") or provenance.get("advisory")

        # Determine annotation state
        verif_status = str(item.get("verification_status", "GROUND_TRUTH_VERIFIED")).upper()
        is_buggy = bool(item.get("is_buggy", True))

        raw_state = item.get("annotation_state")
        if raw_state:
            annot_state = AnnotationState(raw_state)
        elif not is_buggy:
            annot_state = AnnotationState.CLEAN
        elif "VERIFIED" in verif_status:
            annot_state = AnnotationState.VERIFIED
        else:
            annot_state = AnnotationState.UNKNOWN

        # Determine annotation completeness
        raw_comp = item.get("annotation_completeness")
        if raw_comp:
            completeness = AnnotationCompleteness(raw_comp)
        elif not is_buggy:
            completeness = AnnotationCompleteness.EXHAUSTIVE
        else:
            completeness = AnnotationCompleteness.PARTIAL

        mc = ManifestCase(
            case_id=item["case_id"],
            paired_case_id=item.get("paired_case_id"),
            repository=item["repository"],
            commit_hash=item["commit_hash"],
            buggy_commit=item.get("buggy_commit"),
            fixed_commit=item.get("fixed_commit"),
            target_file=item["target_file"],
            fixture_path=item.get("fixture_path"),
            language=item.get("language", "python"),
            is_buggy=is_buggy,
            annotation_state=annot_state,
            annotation_completeness=completeness,
            category_id=item.get("category_id"),
            reviewed_categories=item.get("reviewed_categories") or [],
            target_scope=item.get("target_scope"),
            intended_behavior=item.get("intended_behavior"),
            validation_notes=item.get("validation_notes"),
            primary_cwe=item.get("primary_cwe"),
            acceptable_alternative_cwes=item.get("acceptable_alternative_cwes") or [],
            line_ranges=item.get("line_ranges") or [],
            defects=item.get("defects") or [],
            reproducer=item.get("reproducer"),
            reproducer_status=item.get("reproducer_status", "not_attempted"),
            source_reference=src_ref,
            contextual_files=item.get("contextual_files") or [],
            synthetic=bool(item.get("synthetic", False)),
            source_type=item.get("source_type"),
            provenance=item.get("provenance") or {},
        )
        parsed_cases.append(mc)

    return BenchmarkManifest(
        description=data.get("description", "AI Code Auditor Benchmark Manifest"),
        cases=parsed_cases,
    )
