"""Comprehensive integration and unit tests for GitHub Webhook intake endpoint."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auditor.api.app import create_app
from auditor.api.processor import IAuditProcessor
from auditor.api.webhooks import get_audit_processor, set_audit_processor, set_session_provider
from auditor.db.models import Base
from auditor.db.repository import AuditRepository
from auditor.db.session import get_db

TEST_SECRET = "super-secret-webhook-key-12345"


def compute_signature(payload_bytes: bytes, secret: str = TEST_SECRET) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class MockAuditProcessor(IAuditProcessor):
    """Deterministic mock audit processor for testing intake workflow."""

    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
        self.processed_audits: list[str] = []

    def process_audit(self, audit_id: str, session) -> None:
        self.processed_audits.append(audit_id)
        repo = AuditRepository(session)
        if self.should_fail:
            repo.update_audit_status(audit_id, status="failed", error_message="Mock failure in processor")
        else:
            repo.update_audit_status(audit_id, status="completed", duration_seconds=0.5)
        session.commit()


@pytest.fixture
def webhook_client(monkeypatch, tmp_path):
    """Provide FastAPI test client configured with an isolated SQLite DB file and mock processor."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_SECRET)

    db_file = tmp_path / "test_webhook.db"
    db_url = f"sqlite:///{db_file}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    mock_proc = MockAuditProcessor()
    set_audit_processor(mock_proc)
    set_session_provider(override_get_db)

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_audit_processor] = lambda: mock_proc

    with TestClient(app) as client:
        client.mock_processor = mock_proc
        client.session_factory = session_factory
        yield client

    Base.metadata.drop_all(bind=engine)
    set_audit_processor(None)
    set_session_provider(get_db)


def test_webhook_missing_signature(webhook_client):
    body = json.dumps({"action": "opened"}).encode("utf-8")
    resp = webhook_client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={"X-GitHub-Event": "pull_request", "Content-Type": "application/json"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "MISSING_SIGNATURE"


def test_webhook_invalid_signature_format(webhook_client):
    body = json.dumps({"action": "opened"}).encode("utf-8")
    resp = webhook_client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "invalidformat12345",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 401
    data = resp.json()
    assert data["error"]["code"] == "INVALID_SIGNATURE_FORMAT"


def test_webhook_mismatched_signature(webhook_client):
    body = json.dumps({"action": "opened"}).encode("utf-8")
    bad_sig = compute_signature(body, secret="wrong-secret")
    resp = webhook_client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": bad_sig,
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 401
    data = resp.json()
    assert data["error"]["code"] == "INVALID_SIGNATURE"


def test_webhook_unconfigured_secret(webhook_client, monkeypatch):
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    body = json.dumps({"action": "opened"}).encode("utf-8")
    sig = compute_signature(body)
    resp = webhook_client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 500
    data = resp.json()
    assert data["error"]["code"] == "CONFIG_ERROR"


def test_webhook_malformed_json(webhook_client):
    body = b"{not-valid-json:"
    sig = compute_signature(body)
    resp = webhook_client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "INVALID_JSON"


def test_webhook_ignored_event_type(webhook_client):
    payload = {"zen": "Keep it logically awesome."}
    body = json.dumps(payload).encode("utf-8")
    sig = compute_signature(body)
    resp = webhook_client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "ignored"
    assert "ping" in data["message"]


def test_webhook_ignored_pr_action(webhook_client):
    payload = {
        "action": "labeled",
        "number": 1,
        "repository": {"full_name": "test/repo"},
        "pull_request": {"head": {"sha": "a" * 40}},
    }
    body = json.dumps(payload).encode("utf-8")
    sig = compute_signature(body)
    resp = webhook_client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "ignored"
    assert "labeled" in data["message"]


def test_webhook_missing_coordinates(webhook_client):
    payload = {
        "action": "opened",
        "repository": {"full_name": ""},
        "pull_request": {"head": {"sha": ""}},
    }
    body = json.dumps(payload).encode("utf-8")
    sig = compute_signature(body)
    resp = webhook_client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["error"]["code"] == "MISSING_COORDINATES"


def test_webhook_successful_acceptance_and_idempotency(webhook_client):
    payload = {
        "action": "opened",
        "number": 42,
        "repository": {
            "full_name": "pallets/werkzeug",
            "html_url": "https://github.com/pallets/werkzeug",
        },
        "pull_request": {
            "number": 42,
            "head": {"sha": "50cfeebcb01234567890abcdef1234567890abc1"},
            "base": {"sha": "2767bcb10a1234567890abcdef1234567890abc2"},
        },
    }
    body = json.dumps(payload).encode("utf-8")
    sig = compute_signature(body)
    delivery_id = "delivery-uuid-999"

    resp = webhook_client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
            "X-GitHub-Delivery": delivery_id,
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "pending"
    assert data["repository_id"] == "pallets/werkzeug"
    assert data["pr_number"] == 42
    audit_id = data["audit_id"]
    assert audit_id.startswith("audit-")

    # Verify background execution was triggered
    assert audit_id in webhook_client.mock_processor.processed_audits

    # Verify database persistence
    session = webhook_client.session_factory()
    repo = AuditRepository(session)
    record = repo.get_audit(audit_id)
    assert record is not None
    assert record.repository.full_name == "pallets/werkzeug"
    assert record.delivery_id == delivery_id
    # Since mock processor ran, status should be completed
    assert record.status == "completed"
    session.close()

    # Repeated delivery with identical X-GitHub-Delivery (idempotency)
    resp2 = webhook_client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
            "X-GitHub-Delivery": delivery_id,
            "Content-Type": "application/json",
        },
    )
    assert resp2.status_code == 202
    data2 = resp2.json()
    assert data2["audit_id"] == audit_id
    assert "Duplicate delivery" in data2["message"]


def test_dispatcher_processor_execution_without_workspace(webhook_client):
    """Test DispatcherAuditProcessor gracefully fails when workspace is missing for diff acquisition."""
    from auditor.api.processor import DispatcherAuditProcessor
    from auditor.db.repository import AuditRepository

    proc = DispatcherAuditProcessor()

    session = webhook_client.session_factory()
    repo = AuditRepository(session)
    r = repo.get_or_create_repository("test/repo")
    audit = repo.create_audit(
        repository_id=r.id,
        request_id="test-req-dispatcher",
        head_commit="f" * 40,
        configuration="A",
    )
    session.commit()

    # Execute processor
    proc.process_audit(audit.id, session)

    # Verify audit transitioned to failed with descriptive error
    updated = repo.get_audit(audit.id)
    assert updated.status == "failed"
    assert updated.error_message is not None
    assert "Diff acquisition failed" in updated.error_message
    session.close()


def test_webhook_retrievability_and_deduplication(webhook_client):
    """Prove end-to-end retrievability via GET /api/v1/audits/{id} and zero duplicate background runs."""
    payload = {
        "action": "synchronize",
        "number": 88,
        "repository": {
            "full_name": "tiangolo/fastapi",
            "html_url": "https://github.com/tiangolo/fastapi",
        },
        "pull_request": {
            "number": 88,
            "head": {"sha": "90120dd6e81234567890abcdef1234567890abcd"},
            "base": {"sha": "210af1fd3d1234567890abcdef1234567890abcd"},
        },
    }
    body = json.dumps(payload).encode("utf-8")
    sig = compute_signature(body)
    delivery_id = "delivery-uuid-fastapi-88"

    # Step 1: Initial delivery
    resp = webhook_client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
            "X-GitHub-Delivery": delivery_id,
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 202
    audit_id = resp.json()["audit_id"]

    # Step 2: Retrieve outcome via GET /api/v1/audits/{audit_id}
    get_resp = webhook_client.get(f"/api/v1/audits/{audit_id}")
    assert get_resp.status_code == 200
    audit_data = get_resp.json()
    assert audit_data["audit_id"] == audit_id
    assert audit_data["status"] == "completed"
    assert audit_data["pr_number"] == 88
    assert audit_data["head_commit"] == "90120dd6e81234567890abcdef1234567890abcd"

    # Step 3: Duplicate delivery must NOT invoke processor a second time
    initial_processed_count = len(webhook_client.mock_processor.processed_audits)
    resp_dup = webhook_client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
            "X-GitHub-Delivery": delivery_id,
            "Content-Type": "application/json",
        },
    )
    assert resp_dup.status_code == 202
    assert resp_dup.json()["audit_id"] == audit_id
    # Ensure processor was NOT called again
    assert len(webhook_client.mock_processor.processed_audits) == initial_processed_count


def test_webhook_database_failure_rejection(webhook_client, monkeypatch):
    """Ensure database failures during webhook intake produce 500 error and prevent job scheduling."""
    from unittest.mock import patch

    payload = {
        "action": "opened",
        "number": 99,
        "repository": {"full_name": "org/repo", "html_url": "https://github.com/org/repo"},
        "pull_request": {
            "number": 99,
            "head": {"sha": "a" * 40},
            "base": {"sha": "b" * 40},
        },
    }
    body = json.dumps(payload).encode("utf-8")
    sig = compute_signature(body)

    initial_run_count = len(webhook_client.mock_processor.processed_audits)

    with patch.object(AuditRepository, "create_audit", side_effect=RuntimeError("Simulated DB disk failure")):
        resp = webhook_client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-Hub-Signature-256": sig,
                "X-GitHub-Delivery": "delivery-fail-test",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 500
        data = resp.json()
        assert data["error"]["code"] == "DATABASE_PERSISTENCE_ERROR"

    # Verify background task was NEVER scheduled or executed
    assert len(webhook_client.mock_processor.processed_audits) == initial_run_count
