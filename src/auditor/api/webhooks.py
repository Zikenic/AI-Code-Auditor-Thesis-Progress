"""GitHub webhook intake routes and background task scheduling."""

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from auditor.api.processor import DispatcherAuditProcessor, IAuditProcessor
from auditor.api.schemas import ErrorResponse, WebhookAcceptedResponse, WebhookIgnoredResponse
from auditor.api.security import WebhookSecurityError, verify_github_signature
from auditor.db.repository import AuditRepository
from auditor.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

# Injectable audit processor dependency
_audit_processor: IAuditProcessor | None = None


def get_audit_processor() -> IAuditProcessor:
    """Provide audit processor instance."""
    global _audit_processor
    if _audit_processor is None:
        _audit_processor = DispatcherAuditProcessor()
    return _audit_processor


def set_audit_processor(processor: IAuditProcessor | None) -> None:
    """Override audit processor (used in testing)."""
    global _audit_processor
    _audit_processor = processor


_session_provider = get_db


def set_session_provider(provider: Any) -> None:
    """Override session provider factory for background tasks."""
    global _session_provider
    _session_provider = provider


def get_session_provider() -> Any:
    return _session_provider


def execute_background_audit(audit_id: str, processor: IAuditProcessor) -> None:
    """Background task runner ensuring an isolated session is used for execution."""
    session_gen = _session_provider()
    session: Session = next(session_gen)
    try:
        processor.process_audit(audit_id, session)
    finally:
        try:
            next(session_gen, None)
        except StopIteration:
            pass


@router.post(
    "/github",
    response_model=WebhookAcceptedResponse | WebhookIgnoredResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def handle_github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    configuration: str = "A",
    x_github_event: str | None = Header(None, alias="X-GitHub-Event"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
    x_github_delivery: str | None = Header(None, alias="X-GitHub-Delivery"),
    db: Session = Depends(get_db),  # noqa: B008
    processor: IAuditProcessor = Depends(get_audit_processor),  # noqa: B008
) -> Any:
    """Handle incoming GitHub webhook events with HMAC-SHA256 authentication and idempotency."""
    # 1. Read raw body bytes
    raw_body = await request.body()

    # 2. Verify signature
    try:
        verify_github_signature(raw_body, x_hub_signature_256)
    except WebhookSecurityError as sec_err:
        raise HTTPException(
            status_code=sec_err.status_code,
            detail={"code": sec_err.code, "message": sec_err.message, "details": None},
        ) from sec_err

    # 3. Validate JSON payload
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as parse_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_JSON",
                "message": f"Malformed JSON request payload: {str(parse_err)}",
                "details": None,
            },
        ) from parse_err

    # 4. Check event type
    if x_github_event != "pull_request":
        logger.info("Ignoring non-pull_request event: %s", x_github_event)
        return WebhookIgnoredResponse(
            status="ignored",
            message=f"Event '{x_github_event}' is acknowledged but ignored. Only 'pull_request' events are audited.",
        )

    # 5. Check PR action (only opened, synchronize, reopened)
    action = payload.get("action")
    supported_actions = {"opened", "synchronize", "reopened"}
    if action not in supported_actions:
        logger.info("Ignoring unsupported PR action: %s", action)
        return WebhookIgnoredResponse(
            status="ignored",
            message=f"Action '{action}' is acknowledged but ignored. Supported actions: {supported_actions}.",
        )

    # 6. Validate mandatory PR payload structure
    pr = payload.get("pull_request")
    repo_data = payload.get("repository")
    if not isinstance(pr, dict) or not isinstance(repo_data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_PAYLOAD_STRUCTURE",
                "message": "Missing 'pull_request' or 'repository' payload object.",
                "details": None,
            },
        )

    full_name = repo_data.get("full_name")
    html_url = repo_data.get("html_url")
    pr_number = payload.get("number") or pr.get("number")
    head_sha = pr.get("head", {}).get("sha") if isinstance(pr.get("head"), dict) else None
    base_sha = pr.get("base", {}).get("sha") if isinstance(pr.get("base"), dict) else None

    if not full_name or not head_sha:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MISSING_COORDINATES",
                "message": "Repository full_name and pull_request head sha are required.",
                "details": {"repository": full_name, "head_sha": head_sha},
            },
        )

    from auditor.api.audits import validate_repository_and_commit
    validate_repository_and_commit(full_name, head_sha)

    repo = AuditRepository(db)

    # 7. Idempotency check via delivery_id
    if x_github_delivery:
        existing_audit = repo.get_audit_by_delivery_id(x_github_delivery)
        if existing_audit:
            logger.info("Duplicate delivery received: %s, returning existing audit %s", x_github_delivery, existing_audit.id)
            return WebhookAcceptedResponse(
                audit_id=existing_audit.id,
                status=existing_audit.status,
                repository_id=full_name,
                pr_number=existing_audit.pr_number,
                head_commit=existing_audit.head_commit,
                message="Duplicate delivery acknowledged. Existing audit retained.",
            )

    # 8. Persist repository and audit records atomically
    try:
        repository_record = repo.get_or_create_repository(full_name=full_name, html_url=html_url)

        selected_config = payload.get("configuration") or configuration
        request_id = f"gh-webhook-{uuid.uuid4().hex}"
        audit_record = repo.create_audit(
            repository_id=repository_record.id,
            request_id=request_id,
            head_commit=head_sha,
            base_commit=base_sha,
            pr_number=pr_number,
            configuration=selected_config,
            delivery_id=x_github_delivery,
            provenance={"trigger": "github_webhook", "action": action, "delivery_id": x_github_delivery},
        )
        db.commit()
    except Exception as db_err:
        db.rollback()
        logger.exception("Database persistence failed for webhook delivery: %s", db_err)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "DATABASE_PERSISTENCE_ERROR",
                "message": f"Database failure persisting incoming audit job: {str(db_err)}",
                "details": None,
            },
        ) from db_err

    # 9. Schedule background execution only after commit
    background_tasks.add_task(execute_background_audit, audit_record.id, processor)

    return WebhookAcceptedResponse(
        audit_id=audit_record.id,
        status="pending",
        repository_id=full_name,
        pr_number=pr_number,
        head_commit=head_sha,
        message="Audit enqueued for background execution.",
    )
