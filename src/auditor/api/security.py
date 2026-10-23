"""Security utilities for GitHub webhook signature validation."""

import hashlib
import hmac
import os


class WebhookSecurityError(Exception):
    """Base exception for webhook verification failures."""

    def __init__(self, code: str, message: str, status_code: int = 401):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def get_webhook_secret() -> str | None:
    """Retrieve webhook shared secret from environment."""
    return os.environ.get("GITHUB_WEBHOOK_SECRET")


def verify_github_signature(
    raw_payload: bytes,
    signature_header: str | None,
    secret: str | None = None,
) -> bool:
    """Validate X-Hub-Signature-256 header against computed HMAC-SHA256 digest of raw body.

    Raises WebhookSecurityError with appropriate code and message if invalid.
    """
    configured_secret = secret or get_webhook_secret()
    if not configured_secret:
        raise WebhookSecurityError(
            code="CONFIG_ERROR",
            message="Server webhook secret is not configured.",
            status_code=500,
        )

    if not signature_header:
        raise WebhookSecurityError(
            code="MISSING_SIGNATURE",
            message="Missing X-Hub-Signature-256 header.",
            status_code=401,
        )

    if not signature_header.startswith("sha256="):
        raise WebhookSecurityError(
            code="INVALID_SIGNATURE_FORMAT",
            message="Signature header must start with 'sha256='.",
            status_code=401,
        )

    received_digest = signature_header[len("sha256=") :]
    computed_digest = hmac.new(
        configured_secret.encode("utf-8"),
        raw_payload,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(received_digest, computed_digest):
        raise WebhookSecurityError(
            code="INVALID_SIGNATURE",
            message="Provided X-Hub-Signature-256 header does not match computed HMAC digest.",
            status_code=401,
        )

    return True
