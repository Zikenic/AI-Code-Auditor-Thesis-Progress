"""Audit request domain model."""

from pydantic import BaseModel, Field

from auditor.models.config import AuditConfiguration


class AuditRequest(BaseModel):
    """Request payload to initiate a Pull Request code audit."""

    request_id: str = Field(..., description="Unique idempotency identifier for this audit request.")
    repository_id: str = Field(..., description="Repository full name or ID (e.g. 'owner/repo').")
    pr_number: int | None = Field(default=None, description="Pull Request number if triggered via PR event.")
    head_commit: str = Field(..., description="Commit SHA of PR head to be audited.")
    base_commit: str | None = Field(default=None, description="Commit SHA of PR base branch for computing diff.")
    configuration: AuditConfiguration = Field(
        default=AuditConfiguration.D,
        description="Active evaluation configuration (A, B, C, or D).",
    )
    workspace_path: str | None = Field(
        default=None,
        description="Local directory path of checked-out repository working tree if available.",
    )
