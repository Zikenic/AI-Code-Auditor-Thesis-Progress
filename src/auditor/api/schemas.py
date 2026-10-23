"""API request, response, and error envelope schemas."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Inner error payload for the canonical JSON error envelope."""

    code: str = Field(..., description="Stable machine-readable error token.")
    message: str = Field(..., description="Human-readable explanation.")
    details: Any = Field(default=None, description="Diagnostic data or validation error details.")


class ErrorResponse(BaseModel):
    """Canonical project-specific JSON error envelope."""

    error: ErrorDetail


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(default="healthy", description="Application readiness status.")
    database: str = Field(default="connected", description="Database connection health.")
    version: str = Field(default="0.1.0", description="API version.")


class WebhookAcceptedResponse(BaseModel):
    """Response returned upon successful webhook acceptance and audit enqueue."""

    audit_id: str = Field(..., description="Stable audit resource identifier.")
    status: str = Field(default="pending", description="Initial lifecycle state.")
    repository_id: str = Field(..., description="Repository full name.")
    pr_number: int | None = Field(default=None, description="Pull Request number.")
    head_commit: str = Field(..., description="Commit SHA of PR head.")
    message: str = Field(default="Audit enqueued for background execution.", description="Informational message.")


class WebhookIgnoredResponse(BaseModel):
    """Response returned when an authenticated event is ignored."""

    status: str = Field(default="ignored", description="Event was received and ignored.")
    message: str = Field(..., description="Reason the event was ignored.")


class AuditCreateRequest(BaseModel):
    """Direct audit creation request schema."""

    repository: str = Field(..., min_length=1, description="Repository identifier (e.g. 'owner/repo').")
    head_commit: str = Field(..., min_length=1, description="Target commit SHA.")
    base_commit: str | None = Field(default=None, description="Base commit SHA for differential analysis.")
    pr_number: int | None = Field(default=None, description="Associated Pull Request number if applicable.")
    configuration: str = Field(default="D", description="Audit configuration (A, B, C, or D).")
    workspace_path: str | None = Field(default=None, description="Path to local checked-out workspace.")
    sync: bool = Field(default=False, description="Whether to execute synchronously before returning.")


class FindingDetail(BaseModel):
    """Normalized finding representation in audit detail response."""

    id: str
    tool_name: str
    detection_layer: str
    category_id: int
    primary_cwe: str
    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    severity: str
    title: str
    description: str


class AuditResponse(BaseModel):
    """Detailed audit representation."""

    audit_id: str
    request_id: str
    status: str
    repository: str
    head_commit: str
    base_commit: str | None = None
    pr_number: int | None = None
    configuration: str
    created_at: str
    completed_at: str | None = None
    duration_seconds: float | None = None
    error_message: str | None = None
    finding_count: int = 0
    findings: list[FindingDetail] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
