"""Ground truth defect and benchmark case domain models."""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

from auditor.models.taxonomy import ACTIVE_TAXONOMY


class ImpactType(StrEnum):
    """Impact attribute for Category 1 defects."""

    FUNCTIONAL = "functional"
    SECURITY = "security"


class ReproducerStatus(StrEnum):
    """Execution status for candidate reproduction."""

    EXECUTED_CONFIRMED = "executed_confirmed"
    EXECUTED_NOT_REPRODUCED = "executed_not_reproduced"
    ATTEMPTED_BLOCKED = "attempted_blocked"
    CITED_NOT_RUN = "cited_not_run"
    HISTORICAL_CLAIM_UNVERIFIED = "historical_claim_unverified"
    NOT_ATTEMPTED = "not_attempted"


class GroundTruthDefect(BaseModel):
    """Ground-truth verified defect in a benchmark case."""

    defect_id: str = Field(..., description="Unique defect ID (e.g. 'DEF-0001').")
    category_id: int = Field(..., description="Taxonomy category ID (1..6 default, up to 8 if approved).")
    impact: ImpactType | None = Field(
        default=None,
        description="Required for Category 1 (functional vs security). Must be None for Categories 2..6.",
    )
    primary_cwe: str = Field(..., description="Primary CWE identifier (e.g., 'CWE-89').")
    acceptable_alternative_cwes: set[str] = Field(
        default_factory=set,
        description="Pre-declared acceptable alternative CWE set (at most 2 alternatives, max 3 labels total).",
    )
    file_path: str = Field(..., description="Repository-relative target file path in buggy pre-fix state.")
    start_line: int = Field(..., ge=1, description="1-indexed ground truth defect start line.")
    end_line: int = Field(..., ge=1, description="1-indexed ground truth defect end line.")
    description: str | None = Field(default=None, description="Documented defect description.")

    @field_validator("primary_cwe")
    @classmethod
    def normalize_primary_cwe(cls, v: str) -> str:
        clean = v.strip().upper()
        if not clean.startswith("CWE-") and clean.isdigit():
            clean = f"CWE-{clean}"
        return clean

    @field_validator("acceptable_alternative_cwes")
    @classmethod
    def normalize_alternative_cwes(cls, v: set[str]) -> set[str]:
        cleaned = set()
        for item in v:
            c = item.strip().upper()
            if not c.startswith("CWE-") and c.isdigit():
                c = f"CWE-{c}"
            cleaned.add(c)
        if len(cleaned) > 2:
            raise ValueError(
                f"Methodology limits pre-declared alternative CWEs to at most 2 (received {len(cleaned)})."
            )
        return cleaned

    @field_validator("category_id")
    @classmethod
    def validate_category(cls, v: int) -> int:
        return ACTIVE_TAXONOMY.validate_category(v)

    @model_validator(mode="after")
    def validate_category_1_impact_and_lines(self) -> "GroundTruthDefect":
        # Validate Category 1 impact rule
        if self.category_id == 1:
            if self.impact is None:
                raise ValueError("Category 1 defects MUST explicitly declare impact as 'functional' or 'security'.")
        else:
            if self.impact is not None:
                raise ValueError(
                    f"Category {self.category_id} defects must have impact=None; impact is only applicable to Category 1."
                )

        # Validate line range
        if self.end_line < self.start_line:
            raise ValueError(f"end_line ({self.end_line}) cannot be less than start_line ({self.start_line}).")
        return self

    def matches_cwe(self, predicted_cwe: str) -> bool:
        """Check if predicted CWE matches primary CWE or falls in pre-declared alternative set."""
        norm_pred = predicted_cwe.strip().upper()
        if not norm_pred.startswith("CWE-") and norm_pred.isdigit():
            norm_pred = f"CWE-{norm_pred}"
        return norm_pred == self.primary_cwe or norm_pred in self.acceptable_alternative_cwes


class BenchmarkCase(BaseModel):
    """Benchmark evaluation test case (buggy PR or clean PR)."""

    case_id: str = Field(..., description="Unique case identifier (e.g. 'CAND-0001' or 'BENCH-001').")
    repository: str = Field(..., description="Repository full name (e.g. 'encode/starlette').")
    commit_hash: str = Field(..., description="Target git commit SHA.")
    is_buggy: bool = Field(..., description="True if case contains ground-truth defect; False if clean PR.")
    verification_status: str = Field(
        default="GROUND_TRUTH_VERIFIED",
        description="Verification lifecycle status (e.g. GROUND_TRUTH_VERIFIED, SOURCE_VERIFIED, PENDING_DECISION).",
    )
    reproducer_status: ReproducerStatus = Field(
        default=ReproducerStatus.NOT_ATTEMPTED,
        description="Execution status for candidate reproduction.",
    )
    contextual_files: list[str] = Field(
        default_factory=list,
        description="Associated non-buggy contextual files (e.g. constants, headers).",
    )
    defects: list[GroundTruthDefect] = Field(
        default_factory=list,
        description="List of ground-truth defects in this case (empty for clean PRs).",
    )

    @model_validator(mode="after")
    def validate_case_consistency(self) -> "BenchmarkCase":
        if self.is_buggy and len(self.defects) == 0:
            raise ValueError(f"Buggy case '{self.case_id}' must declare at least one ground-truth defect.")
        if not self.is_buggy and len(self.defects) > 0:
            raise ValueError(f"Clean case '{self.case_id}' cannot contain ground-truth defects.")
        return self
