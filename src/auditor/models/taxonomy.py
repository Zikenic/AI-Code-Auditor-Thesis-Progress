"""Taxonomy configuration and category validation."""

from pydantic import BaseModel, Field, field_validator

# Default locked taxonomy: 6 core categories
DEFAULT_APPROVED_CATEGORIES: set[int] = {1, 2, 3, 4, 5, 6}

# Maximum ceiling permitted under locked methodology expansion rule (initial 6 + max 2)
MAX_PERMISSIBLE_TAXONOMY_CATEGORIES: int = 8

CATEGORY_NAMES: dict[int, str] = {
    1: "Boundary / conditional / logic defects",
    2: "Input validation / sanitization",
    3: "SQL / ORM injection",
    4: "Path traversal / unsafe file operations",
    5: "Authentication",
    6: "Authorization",
}


class TaxonomyConfig(BaseModel):
    """Configuration defining the active, approved defect categories for an evaluation or runtime.

    Enforces the thesis methodology rule: default 6 categories, with up to 2 justified
    additions (cap of 8 total). Categories 7 and 8 are permitted only when explicitly approved
    in this configuration.
    """

    approved_category_ids: set[int] = Field(
        default_factory=lambda: set(DEFAULT_APPROVED_CATEGORIES),
        description="Set of actively approved category IDs for this environment.",
    )

    @field_validator("approved_category_ids")
    @classmethod
    def validate_category_bounds(cls, v: set[int]) -> set[int]:
        if not v:
            raise ValueError("Approved taxonomy categories cannot be empty.")
        for cat_id in v:
            if cat_id < 1 or cat_id > MAX_PERMISSIBLE_TAXONOMY_CATEGORIES:
                raise ValueError(
                    f"Category ID {cat_id} exceeds permissible taxonomy bounds "
                    f"[1, {MAX_PERMISSIBLE_TAXONOMY_CATEGORIES}]."
                )
        return v

    def is_approved(self, category_id: int) -> bool:
        """Check if a category ID is actively approved."""
        return category_id in self.approved_category_ids

    def validate_category(self, category_id: int) -> int:
        """Validate category ID against active configuration, raising ValueError if not approved."""
        if not self.is_approved(category_id):
            raise ValueError(
                f"Category ID {category_id} is not in the active approved taxonomy "
                f"{sorted(self.approved_category_ids)}. Adding Category 7 or 8 requires "
                "formal methodology justification and explicit taxonomy approval."
            )
        return category_id


# Default global instance
ACTIVE_TAXONOMY = TaxonomyConfig()
