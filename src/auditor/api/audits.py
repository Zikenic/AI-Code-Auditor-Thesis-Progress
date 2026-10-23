"""Direct audit creation and inspection API endpoints."""

from __future__ import annotations

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auditor.api.schemas import (
    AuditCreateRequest,
    AuditResponse,
    ErrorResponse,
    FindingDetail,
)
from auditor.api.webhooks import execute_background_audit, get_audit_processor
from auditor.db.models import AuditRecord
from auditor.db.repository import AuditRepository
from auditor.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/audits", tags=["audits"])

REPO_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?$")
COMMIT_REF_RE = re.compile(r"^[A-Za-z0-9_./-]{1,64}$")


def validate_workspace_path(path_str: str | None) -> str | None:
    """Validate that workspace_path resides strictly within an authorized directory root."""
    if not path_str:
        return None

    target = Path(path_str).resolve()
    if not target.exists() or not target.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_WORKSPACE_PATH",
                "message": f"Workspace directory does not exist: '{path_str}'.",
                "details": {"workspace_path": path_str},
            },
        )

    # Allowed roots: Current workspace repository root, and explicitly configured AUDITOR_ALLOWED_WORKSPACE_ROOTS.
    # Security Note: The shared OS temp directory is NOT globally allowed by default to prevent
    # unauthorized reading or auditing of sensitive files in shared temporary storage.
    allowed_roots = [
        Path.cwd().resolve(),
    ]
    env_roots = os.environ.get("AUDITOR_ALLOWED_WORKSPACE_ROOTS", "")
    for root in env_roots.split(","):
        if root.strip():
            allowed_roots.append(Path(root.strip()).resolve())

    is_allowed = any(target.is_relative_to(root) for root in allowed_roots)
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FORBIDDEN_WORKSPACE_PATH",
                "message": f"Workspace path '{path_str}' is outside permitted workspace roots.",
                "details": {"workspace_path": path_str},
            },
        )

    return str(target)


def validate_repository_and_commit(repository: str, head_commit: str) -> None:
    """Sanitize repository name and commit reference to prevent path escaping or shell abuse."""
    if not REPO_NAME_RE.match(repository):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_REPOSITORY_NAME",
                "message": f"Invalid repository identifier: '{repository}'.",
                "details": {"repository": repository},
            },
        )
    if not COMMIT_REF_RE.match(head_commit) or ".." in head_commit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_COMMIT_REF",
                "message": f"Invalid commit reference: '{head_commit}'.",
                "details": {"head_commit": head_commit},
            },
        )


def _serialize_audit(audit: AuditRecord) -> AuditResponse:
    """Format SQLAlchemy AuditRecord into AuditResponse schema."""
    findings = [
        FindingDetail(
            id=f.id,
            tool_name=f.tool_name,
            detection_layer=f.detection_layer,
            category_id=f.category_id,
            primary_cwe=f.primary_cwe,
            file_path=f.file_path,
            start_line=f.start_line,
            end_line=f.end_line,
            severity=f.severity,
            title=f.title,
            description=f.description,
        )
        for f in audit.findings
    ]

    return AuditResponse(
        audit_id=audit.id,
        request_id=audit.request_id,
        status=audit.status,
        repository=audit.repository.full_name if audit.repository else "unknown",
        head_commit=audit.head_commit,
        base_commit=audit.base_commit,
        pr_number=audit.pr_number,
        configuration=audit.configuration,
        created_at=audit.created_at.isoformat(),
        completed_at=audit.completed_at.isoformat() if audit.completed_at else None,
        duration_seconds=audit.duration_seconds,
        error_message=audit.error_message,
        finding_count=len(findings),
        findings=findings,
        provenance=audit.provenance or {},
    )


@router.post(
    "",
    response_model=AuditResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {"model": ErrorResponse, "description": "Validation failed."},
        500: {"model": ErrorResponse, "description": "Internal server error."},
    },
)
def create_audit(
    request: AuditCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),  # noqa: B008
) -> AuditResponse:
    """Trigger a new code audit directly for a specified repository and commit."""
    validate_repository_and_commit(request.repository, request.head_commit)
    validated_ws = validate_workspace_path(request.workspace_path)

    repo = AuditRepository(db)
    repository_record = repo.get_or_create_repository(request.repository)

    request_id = f"req-{uuid.uuid4().hex[:12]}"
    provenance: dict[str, Any] = {
        "trigger": "direct_api",
        "configuration": request.configuration,
    }
    if validated_ws:
        provenance["workspace_path"] = validated_ws

    audit = repo.create_audit(
        repository_id=repository_record.id,
        request_id=request_id,
        head_commit=request.head_commit,
        base_commit=request.base_commit,
        pr_number=request.pr_number,
        configuration=request.configuration,
        provenance=provenance,
    )
    db.commit()

    processor = get_audit_processor()

    if request.sync:
        processor.process_audit(audit.id, db)
        db.refresh(audit)
    else:
        background_tasks.add_task(execute_background_audit, audit.id, processor)

    return _serialize_audit(audit)


@router.get(
    "/{audit_id}",
    response_model=AuditResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Audit not found."},
        500: {"model": ErrorResponse, "description": "Internal server error."},
    },
)
def get_audit(
    audit_id: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> AuditResponse:
    """Retrieve audit execution status and emitted findings by audit identifier."""
    repo = AuditRepository(db)
    audit = repo.get_audit(audit_id)

    if not audit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "AUDIT_NOT_FOUND",
                "message": f"Audit '{audit_id}' does not exist.",
                "details": {"audit_id": audit_id},
            },
        )

    return _serialize_audit(audit)
