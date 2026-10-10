"""Authoritative loader and validator for the 12 Ground-Truth-Verified pilot benchmark cases.

Source of Truth Architecture:
- Ground-truth evidence and human-readable audit trail live in:
  Project Documents/dataset/ground_truth_validation_pilot.md
- Canonical machine-readable dataset consumed by evaluation harness lives in:
  data/pilot_cases.json
- Pydantic models (BenchmarkCase, GroundTruthDefect) are the authoritative runtime validator.
  data/pilot_cases.schema.json serves as a supplementary JSON Schema contract.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from auditor.models.ground_truth import (
    BenchmarkCase,
    GroundTruthDefect,
    ImpactType,
    ReproducerStatus,
)


@dataclass
class PilotCandidateRecord:
    """Structured fields extracted from the pilot case representation."""

    candidate_id: str
    category_id: int | None
    impact_raw: str | None
    repository: str | None
    buggy_commit: str | None
    fixed_commit: str | None
    file_path: str | None
    locus_raw: str | None
    line_ranges: list[tuple[int, int]]
    primary_cwe: str | None
    acceptable_alternative_cwes: set[str]
    reproducer: str | None
    quality_level: str | None
    verification_status: str | None


def get_default_pilot_data_path() -> Path:
    """Resolve the default filesystem path to the canonical data/pilot_cases.json."""
    # Check relative to current working directory
    cwd_path = Path("data/pilot_cases.json")
    if cwd_path.exists():
        return cwd_path.resolve()

    # Search upwards from module location to find repo root containing data/pilot_cases.json
    curr = Path(__file__).resolve().parent
    for _ in range(5):
        candidate = curr / "data" / "pilot_cases.json"
        if candidate.exists():
            return candidate.resolve()
        if curr.parent == curr:
            break
        curr = curr.parent

    return cwd_path.resolve()


def parse_case_dict_to_benchmark_case(case_dict: dict[str, Any]) -> BenchmarkCase:
    """Convert a structured case dictionary into a validated BenchmarkCase.

    Enforces strict model validation:
    - Passes declared impact directly to GroundTruthDefect without silent modification or stripping.
    - Category 1 requires impact in {'functional', 'security'}.
    - Categories 2..6 must have impact=None.
    """
    case_id = case_dict.get("case_id") or case_dict.get("candidate_id")
    if not case_id:
        raise ValueError("Missing 'case_id' or 'candidate_id' in case dictionary.")

    repository = case_dict.get("repository") or ""
    commit_hash = case_dict.get("commit_hash") or case_dict.get("buggy_commit") or ""
    is_buggy = bool(case_dict.get("is_buggy", True))

    defects: list[GroundTruthDefect] = []

    # Priority 1: Direct 'defects' array
    if "defects" in case_dict and isinstance(case_dict["defects"], list) and len(case_dict["defects"]) > 0:
        for raw_defect in case_dict["defects"]:
            raw_impact = raw_defect.get("impact")
            impact_val = ImpactType(raw_impact) if raw_impact is not None else None
            defect = GroundTruthDefect(
                defect_id=raw_defect["defect_id"],
                category_id=raw_defect["category_id"],
                impact=impact_val,
                primary_cwe=raw_defect["primary_cwe"],
                acceptable_alternative_cwes=set(raw_defect.get("acceptable_alternative_cwes", [])),
                file_path=raw_defect["file_path"],
                start_line=raw_defect["start_line"],
                end_line=raw_defect["end_line"],
                description=raw_defect.get("description"),
            )
            defects.append(defect)
    else:
        # Priority 2: Synthesize defects from line_ranges and case-level fields
        line_ranges = case_dict.get("line_ranges", [])
        cat_id = case_dict.get("category_id")
        raw_impact = case_dict.get("impact")
        impact_val = ImpactType(raw_impact) if raw_impact is not None else None
        primary_cwe = case_dict.get("primary_cwe") or ""
        alt_cwes = set(case_dict.get("acceptable_alternative_cwes", []))
        target_file = case_dict.get("target_file") or ""

        for idx, span in enumerate(line_ranges):
            s = span[0]
            e = span[1] if len(span) > 1 else s
            defect = GroundTruthDefect(
                defect_id=f"{case_id}-DEF-{idx + 1}",
                category_id=cat_id,
                impact=impact_val,
                primary_cwe=primary_cwe,
                acceptable_alternative_cwes=alt_cwes,
                file_path=target_file,
                start_line=s,
                end_line=e,
                description=f"Ground-truth locus {s}-{e}",
            )
            defects.append(defect)

    raw_reproducer = case_dict.get("reproducer_status", ReproducerStatus.NOT_ATTEMPTED)
    reproducer_status = ReproducerStatus(raw_reproducer) if isinstance(raw_reproducer, str) else raw_reproducer

    return BenchmarkCase(
        case_id=case_id,
        repository=repository,
        commit_hash=commit_hash,
        is_buggy=is_buggy,
        verification_status=case_dict.get("verification_status", "GROUND_TRUTH_VERIFIED"),
        reproducer_status=reproducer_status,
        contextual_files=case_dict.get("contextual_files", []),
        defects=defects,
    )


def load_pilot_cases_from_json(
    json_path: Path | str | None = None,
    only_verified: bool = False,
) -> list[BenchmarkCase]:
    """Load and validate all pilot benchmark cases from structured JSON.

    Args:
        json_path: Optional path to JSON file. If None, resolves via get_default_pilot_data_path().
        only_verified: If True, only loads cases with verification_status == 'GROUND_TRUTH_VERIFIED'.

    Returns:
        List of strictly validated BenchmarkCase instances.
    """
    path = Path(json_path) if json_path is not None else get_default_pilot_data_path()
    if not path.exists():
        raise FileNotFoundError(f"Pilot cases structured JSON file not found at: {path}")

    content = path.read_text(encoding="utf-8")
    data = json.loads(content)

    cases_raw = data.get("cases", [])
    if not cases_raw:
        raise ValueError(f"No cases found in structured JSON payload at {path}")

    cases: list[BenchmarkCase] = []
    for item in cases_raw:
        if only_verified and item.get("verification_status") != "GROUND_TRUTH_VERIFIED":
            continue
        case = parse_case_dict_to_benchmark_case(item)
        cases.append(case)

    return cases


# Authoritative alias
load_pilot_benchmark_cases = load_pilot_cases_from_json


def validate_pilot_candidate(
    record: PilotCandidateRecord,
    preserve_raw_impact: bool = True,
) -> tuple[BenchmarkCase | None, list[str]]:
    """Validate a candidate record against the BenchmarkCase domain model.

    Retained for testing and backward compatibility.
    """
    errors: list[str] = []

    if not record.repository:
        errors.append("repository: Missing repository identifier in record")
    if not record.buggy_commit:
        errors.append("commit_hash: Missing buggy commit SHA in record")
    if not record.file_path:
        errors.append("file_path: Missing affected file path in record")
    if not record.category_id:
        errors.append("category_id: Missing category ID in record")
    if not record.primary_cwe:
        errors.append("primary_cwe: Missing primary CWE in record")
    if not record.line_ranges:
        errors.append("line_ranges: Missing ground truth line coordinates in record")

    if errors:
        return None, errors

    defects: list[GroundTruthDefect] = []
    for idx, (s, e) in enumerate(record.line_ranges):
        if preserve_raw_impact:
            impact_val = ImpactType(record.impact_raw) if record.impact_raw in ("functional", "security") else None
        else:
            impact_val = (
                ImpactType(record.impact_raw)
                if (record.category_id == 1 and record.impact_raw in ("functional", "security"))
                else None
            )

        try:
            defect = GroundTruthDefect(
                defect_id=f"{record.candidate_id}-DEF-{idx + 1}",
                category_id=record.category_id,
                impact=impact_val,
                primary_cwe=record.primary_cwe,
                acceptable_alternative_cwes=record.acceptable_alternative_cwes,
                file_path=record.file_path.split(" ")[0] if record.file_path else "",
                start_line=s,
                end_line=e,
                description=f"Ground-truth locus {s}-{e}",
            )
            defects.append(defect)
        except ValidationError as ve:
            for err in ve.errors():
                loc = ".".join(str(x) for x in err["loc"])
                errors.append(f"defects.{idx}.{loc}: {err['msg']}")

    if errors:
        return None, errors

    try:
        case = BenchmarkCase(
            case_id=record.candidate_id,
            repository=record.repository or "",
            commit_hash=record.buggy_commit or "",
            is_buggy=True,
            defects=defects,
        )
        return case, []
    except ValidationError as ve:
        for err in ve.errors():
            loc = ".".join(str(x) for x in err["loc"])
            errors.append(f"{loc}: {err['msg']}")
        return None, errors
