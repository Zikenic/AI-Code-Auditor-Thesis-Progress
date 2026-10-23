"""API package exports."""

from auditor.api.app import create_app
from auditor.api.audits import router as audits_router
from auditor.api.processor import DispatcherAuditProcessor, IAuditProcessor
from auditor.api.schemas import (
    AuditCreateRequest,
    AuditResponse,
    ErrorDetail,
    ErrorResponse,
    FindingDetail,
    HealthResponse,
    WebhookAcceptedResponse,
    WebhookIgnoredResponse,
)
from auditor.api.security import WebhookSecurityError, verify_github_signature
from auditor.api.webhooks import router as webhooks_router

__all__ = [
    "AuditCreateRequest",
    "AuditResponse",
    "DispatcherAuditProcessor",
    "ErrorDetail",
    "ErrorResponse",
    "FindingDetail",
    "HealthResponse",
    "IAuditProcessor",
    "WebhookAcceptedResponse",
    "WebhookIgnoredResponse",
    "WebhookSecurityError",
    "audits_router",
    "create_app",
    "verify_github_signature",
    "webhooks_router",
]
