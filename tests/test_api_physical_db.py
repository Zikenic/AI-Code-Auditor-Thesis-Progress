"""Integration tests for FastAPI endpoints and physical database persistence."""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auditor.api.app import create_app
from auditor.api.processor import IAuditProcessor
from auditor.api.webhooks import set_audit_processor, set_session_provider
from auditor.db.models import Base
from auditor.db.repository import AuditRepository
from auditor.db.session import get_db

TEST_WEBHOOK_SECRET = "physical-db-secret-key-9999"


def compute_signature(payload_bytes: bytes, secret: str = TEST_WEBHOOK_SECRET) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class MockSyncAuditProcessor(IAuditProcessor):
    """Predictable processor for testing DB persistence and finding insertion."""

    def process_audit(self, audit_id: str, session) -> None:
        repo = AuditRepository(session)
        audit = repo.get_audit(audit_id)
        if not audit:
            return

        from auditor.models.finding import ConfidenceLevel, DetectionLayer, PredictedFinding, SeverityLevel

        mock_finding = PredictedFinding(
            finding_id=f"find-{audit_id[:8]}",
            detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
            tool_name="semgrep",
            category_id=4,
            primary_cwe="CWE-22",
            file_path="src/service/file_handler.py",
            start_line=45,
            end_line=48,
            severity=SeverityLevel.HIGH,
            confidence=ConfidenceLevel.HIGH,
            title="Unsafe Path Traversal",
            description="User input passed to open() without sanitization.",
        )
        repo.persist_findings(audit_id, [mock_finding])
        repo.update_audit_status(
            audit_id=audit_id,
            status="completed",
            duration_seconds=1.25,
            provenance={"tested_with": "MockSyncAuditProcessor"},
        )
        session.commit()


@pytest.fixture
def physical_db_setup(monkeypatch, tmp_path):
    """Sets up a physical SQLite database file on disk and wires FastAPI test client."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_WEBHOOK_SECRET)

    db_path = tmp_path / "auditor_physical_test.db"
    db_url = f"sqlite:///{db_path}"

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

    mock_proc = MockSyncAuditProcessor()
    set_audit_processor(mock_proc)
    set_session_provider(override_get_db)

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    yield {
        "client": client,
        "db_path": db_path,
        "engine": engine,
        "session_factory": session_factory,
        "processor": mock_proc,
    }

    engine.dispose()
    set_audit_processor(None)
    set_session_provider(get_db)


class TestPhysicalDbAndApiIntegration:
    """End-to-end integration tests using a real file-backed SQLite database."""

    def test_health_check_endpoints(self, physical_db_setup):
        client = physical_db_setup["client"]

        # 1. /health
        res1 = client.get("/health")
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["status"] == "healthy"
        assert data1["database"] == "connected"
        assert data1["version"] == "0.1.0"

        # 2. /api/v1/health
        res2 = client.get("/api/v1/health")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2 == data1

    def test_direct_audit_submission_and_retrieval(self, physical_db_setup):
        client = physical_db_setup["client"]

        # Submit audit synchronously
        payload = {
            "repository": "thesis-org/secure-core",
            "head_commit": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
            "base_commit": "0000000000000000000000000000000000000000",
            "pr_number": 42,
            "configuration": "D",
            "sync": True,
        }

        res = client.post("/api/v1/audits", json=payload)
        assert res.status_code == 201
        created = res.json()
        audit_id = created["audit_id"]
        assert created["repository"] == "thesis-org/secure-core"
        assert created["status"] == "completed"
        assert created["finding_count"] == 1
        assert len(created["findings"]) == 1
        assert created["findings"][0]["primary_cwe"] == "CWE-22"

        # Retrieve audit
        get_res = client.get(f"/api/v1/audits/{audit_id}")
        assert get_res.status_code == 200
        fetched = get_res.json()
        assert fetched["audit_id"] == audit_id
        assert fetched["head_commit"] == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
        assert fetched["duration_seconds"] == 1.25

    def test_persistence_across_connection_restarts(self, physical_db_setup):
        """Verify data remains safely persisted when DB connection is destroyed and reopened."""
        client = physical_db_setup["client"]
        db_path = physical_db_setup["db_path"]

        # 1. Create audit
        payload = {
            "repository": "thesis-org/persistence-check",
            "head_commit": "1111222233334444555566667777888899990000",
            "sync": True,
        }
        create_res = client.post("/api/v1/audits", json=payload)
        assert create_res.status_code == 201
        audit_id = create_res.json()["audit_id"]

        # 2. Simulate complete application/connection teardown
        physical_db_setup["engine"].dispose()

        # 3. Create entirely fresh engine and session directly on the physical file
        fresh_engine = create_engine(f"sqlite:///{db_path}")
        fresh_factory = sessionmaker(bind=fresh_engine)
        with fresh_factory() as session:
            repo = AuditRepository(session)
            saved_audit = repo.get_audit(audit_id)
            assert saved_audit is not None
            assert saved_audit.repository.full_name == "thesis-org/persistence-check"
            assert saved_audit.status == "completed"
            assert len(saved_audit.findings) == 1
            assert saved_audit.findings[0].tool_name == "semgrep"
        fresh_engine.dispose()

    def test_canonical_error_envelopes(self, physical_db_setup):
        client = physical_db_setup["client"]

        # 1. 404 Not Found
        missing_res = client.get("/api/v1/audits/audit-non-existent-999")
        assert missing_res.status_code == 404
        err_404 = missing_res.json()
        assert "error" in err_404
        assert err_404["error"]["code"] == "AUDIT_NOT_FOUND"

        # 2. 422 Validation Error
        invalid_res = client.post("/api/v1/audits", json={"invalid_field": 123})
        assert invalid_res.status_code == 422
        err_422 = invalid_res.json()
        assert "error" in err_422
        assert err_422["error"]["code"] == "VALIDATION_ERROR"
        assert err_422["error"]["details"] is not None

    def test_webhook_intake_persists_to_physical_db(self, physical_db_setup):
        client = physical_db_setup["client"]
        db_path = physical_db_setup["db_path"]

        webhook_payload = {
            "action": "opened",
            "number": 105,
            "pull_request": {
                "head": {"sha": "c0ffee0000111122223333444455556666777788"},
                "base": {"sha": "deadbeef00001111222233334444555566667777"},
            },
            "repository": {
                "full_name": "thesis-org/webhook-tested-repo",
                "html_url": "https://github.com/thesis-org/webhook-tested-repo",
            },
        }
        body_bytes = json.dumps(webhook_payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "deliv-uuid-987654321",
            "X-Hub-Signature-256": compute_signature(body_bytes),
        }

        res = client.post("/api/v1/webhooks/github", content=body_bytes, headers=headers)
        assert res.status_code == 202
        data = res.json()
        audit_id = data["audit_id"]

        # Verify record exists in physical DB
        fresh_engine = create_engine(f"sqlite:///{db_path}")
        with sessionmaker(bind=fresh_engine)() as session:
            repo = AuditRepository(session)
            persisted = repo.get_audit(audit_id)
            assert persisted is not None
            assert persisted.delivery_id == "deliv-uuid-987654321"
            assert persisted.head_commit == "c0ffee0000111122223333444455556666777788"
        fresh_engine.dispose()

    def test_persistence_across_true_subprocess_restart(self, tmp_path):
        """Demonstrate real persistence across an actual operating-system process termination/restart."""
        db_file = tmp_path / "subprocess_test.db"
        script_writer = f"""
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from auditor.db.models import Base
from auditor.db.repository import AuditRepository

engine = create_engine(r"sqlite:///{db_file}")
Base.metadata.create_all(bind=engine)
with sessionmaker(bind=engine)() as session:
    repo = AuditRepository(session)
    r = repo.get_or_create_repository("thesis-org/true-process-test")
    a = repo.create_audit(
        repository_id=r.id,
        request_id="proc-req-001",
        head_commit="abcdef0123456789abcdef0123456789abcdef01",
        configuration="D",
        provenance={{"process_pid": 12345}},
    )
    session.commit()
engine.dispose()
sys.exit(0)
"""
        # Execute writer process
        res_write = subprocess.run([sys.executable, "-c", script_writer], capture_output=True, text=True)
        assert res_write.returncode == 0, f"Subprocess writer failed: {res_write.stderr}"

        # In independent test process, verify data survived the exited process
        verify_engine = create_engine(f"sqlite:///{db_file}")
        with sessionmaker(bind=verify_engine)() as session:
            repo = AuditRepository(session)
            persisted = repo.get_audit_by_request_id("proc-req-001")
            assert persisted is not None
            assert persisted.repository.full_name == "thesis-org/true-process-test"
            assert persisted.head_commit == "abcdef0123456789abcdef0123456789abcdef01"
            assert persisted.provenance["process_pid"] == 12345
        verify_engine.dispose()

    def test_workspace_path_allowlist_enforcement(self, physical_db_setup, tmp_path, monkeypatch):
        client = physical_db_setup["client"]

        # 1. Non-existent path returns 400 INVALID_WORKSPACE_PATH
        bad_path_payload = {
            "repository": "thesis-org/security-check",
            "head_commit": "1111222233334444555566667777888899990000",
            "workspace_path": "/non/existent/path/on/disk",
        }
        res_400 = client.post("/api/v1/audits", json=bad_path_payload)
        assert res_400.status_code == 400
        assert res_400.json()["error"]["code"] == "INVALID_WORKSPACE_PATH"

        # 2. Path outside allowed roots (e.g. root Windows system directory) returns 403 FORBIDDEN_WORKSPACE_PATH
        forbidden_path = "C:\\Windows\\System32" if sys.platform == "win32" else "/etc"
        forbidden_payload = {
            "repository": "thesis-org/security-check",
            "head_commit": "1111222233334444555566667777888899990000",
            "workspace_path": forbidden_path,
        }
        res_403 = client.post("/api/v1/audits", json=forbidden_payload)
        assert res_403.status_code == 403
        assert res_403.json()["error"]["code"] == "FORBIDDEN_WORKSPACE_PATH"

        # 3. An unconfigured arbitrary temp directory returns 403 (shared tempdir NOT globally trusted)
        unconfigured_temp = tmp_path / "unconfigured_temp"
        unconfigured_temp.mkdir()
        unconf_payload = {
            "repository": "thesis-org/security-check",
            "head_commit": "1111222233334444555566667777888899990000",
            "workspace_path": str(unconfigured_temp),
        }
        res_unconf = client.post("/api/v1/audits", json=unconf_payload)
        assert res_unconf.status_code == 403
        assert res_unconf.json()["error"]["code"] == "FORBIDDEN_WORKSPACE_PATH"

        # 4. Valid path inside explicitly allowed root (via AUDITOR_ALLOWED_WORKSPACE_ROOTS) succeeds
        monkeypatch.setenv("AUDITOR_ALLOWED_WORKSPACE_ROOTS", str(tmp_path))
        allowed_dir = tmp_path / "valid_workspace"
        allowed_dir.mkdir()
        allowed_payload = {
            "repository": "thesis-org/security-check",
            "head_commit": "1111222233334444555566667777888899990000",
            "workspace_path": str(allowed_dir),
        }
        res_ok = client.post("/api/v1/audits", json=allowed_payload)
        assert res_ok.status_code == 201
        assert res_ok.json()["provenance"]["workspace_path"] == str(allowed_dir.resolve())

    def test_invalid_repo_coordinates_rejected(self, physical_db_setup):
        client = physical_db_setup["client"]

        # Malicious repository name
        malicious_repo = {
            "repository": "repo; rm -rf /",
            "head_commit": "1111222233334444555566667777888899990000",
        }
        res1 = client.post("/api/v1/audits", json=malicious_repo)
        assert res1.status_code == 400
        assert res1.json()["error"]["code"] == "INVALID_REPOSITORY_NAME"

        # Malicious commit ref with path traversal
        malicious_commit = {
            "repository": "owner/clean-repo",
            "head_commit": "../../../etc/shadow",
        }
        res2 = client.post("/api/v1/audits", json=malicious_commit)
        assert res2.status_code == 400
        assert res2.json()["error"]["code"] == "INVALID_COMMIT_REF"

