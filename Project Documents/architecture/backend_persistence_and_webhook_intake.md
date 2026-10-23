# Backend Persistence and GitHub Webhook Intake Architecture

## 1. Overview

This document describes the implementation of the core persistence layer and GitHub Pull Request Webhook intake service for the AI Code Auditor system.

## 2. Database Layer (`src/auditor/db/`)

- **ORM**: SQLAlchemy 2.0 (`DeclarativeBase`, `Mapped`, `mapped_column`).
- **Engines & Connection**:
  - `DATABASE_URL` environment variable drives the engine configuration.
  - Defaults to SQLite (`sqlite:///./auditor_dev.db`) for isolated local development and testing.
  - Supports PostgreSQL in staging/production deployments.
- **Entities**:
  - `repositories`: Tracks audited repositories (`id`, `full_name`, `html_url`, timestamps).
  - `audits`: Tracks audit lifecycle runs (`id`, `request_id`, `repository_id`, `pr_number`, `head_commit`, `base_commit`, `configuration`, `status`, `error_message`, `delivery_id`, `duration_seconds`, `provenance`, timestamps).
  - `findings`: Persists normalized findings emitted during audit execution (`id`, `audit_id`, `detection_layer`, `tool_name`, `category_id`, `primary_cwe`, `alternative_cwes`, `file_path`, `start_line`, `end_line`, `severity`, `confidence`, `title`, `description`, `suggestion`, `provenance`).
- **Migrations**: Alembic versioning configured in `alembic.ini` and `src/auditor/db/migrations/`.
  - Migration script: `0c5dbcd1df7e_create_repositories_audits_findings_.py`.

## 3. Webhook Intake Service (`src/auditor/api/`)

- **Framework**: FastAPI (`create_app()`).
- **Route**: `POST /api/v1/webhooks/github`
  - Authentication: HMAC-SHA256 signature verification over raw request body using `GITHUB_WEBHOOK_SECRET` (`X-Hub-Signature-256` header).
  - Constant-time comparison: `hmac.compare_digest`.
  - Fail-closed: returns HTTP 500 `CONFIG_ERROR` if server secret is not set.
  - Event filtering: acknowledges only `X-GitHub-Event: pull_request` with actions `opened`, `synchronize`, `reopened`.
  - Idempotency: `X-GitHub-Delivery` uniqueness prevents duplicate audit scheduling on GitHub delivery retries.
  - Transactional safety: Database record committed before scheduling FastAPI `BackgroundTasks`.
  - Response: HTTP `202 Accepted` with `WebhookAcceptedResponse` envelope.
  - Errors: unified **Project-Specific JSON Error Envelope**:
    ```json
    {
      "error": {
        "code": "INVALID_SIGNATURE",
        "message": "...",
        "details": null
      }
    }
    ```

## 4. Dispatcher Integration & Execution Seam (`src/auditor/api/processor.py`)

- **Interface**: `IAuditProcessor` defines `process_audit(audit_id, session)`.
- **Implementation**: `DispatcherAuditProcessor` loads the audit record, maps it to domain `AuditRequest`, and invokes `ConfigurationDispatcher.dispatch()`.
- **Current Integration Boundary**:
  - The webhook provides repository coordinates and commit SHAs, but does **NOT** download source code.
  - If `workspace_path` is missing or diff acquisition fails, the dispatcher transitions the audit to `status = "failed"` with a descriptive error (`Diff acquisition failed`).
  - Real source checkout and PR-diff materialization from GitHub is deferred to the next planned integration phase (GitHub App / Git clone adapter).

## 5. Verification & Testing

- Unit tests:
  - `tests/test_db_persistence.py`: CRUD operations, constraints, lifecycle updates, rollback on errors.
  - `tests/test_webhook_intake.py`: Signature verification (valid/invalid/missing/malformed), payload parsing, event filtering, idempotency, and background processor integration.
- Regression test suite: 154 passing tests (140 baseline + 14 new tests).
