"""End-to-End Vertical Slice Tests: Webhook Intake -> Workspace Materialization -> Config A -> DB Persistence."""

import hashlib
import hmac
import json
import subprocess

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auditor.api.app import create_app
from auditor.api.processor import DispatcherAuditProcessor
from auditor.api.webhooks import get_audit_processor, set_audit_processor, set_session_provider
from auditor.db.models import Base
from auditor.db.repository import AuditRepository
from auditor.db.session import get_db
from auditor.orchestration.git_provider import GitWorkspaceProvider

TEST_SECRET = "vertical-slice-secret-key-999"


def compute_signature(payload_bytes: bytes, secret: str = TEST_SECRET) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


@pytest.fixture
def local_vulnerable_repo(tmp_path):
    """Create a local git repository containing an intentional security issue in head commit."""
    repo_dir = tmp_path / "vulnerable_repo"
    repo_dir.mkdir()

    # Configure git
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "e2e@auditor.local"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "E2E Auditor"], cwd=repo_dir, check=True)

    # Base commit
    base_file = repo_dir / "app.py"
    base_file.write_text("# Safe baseline\ndef run():\n    print('safe')\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)
    base_sha = (
        subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True)
        .stdout.strip()
    )

    # Head commit: introduce vulnerable code in vuln.py
    vuln_file = repo_dir / "vuln.py"
    vuln_file.write_text("import os\nimport sys\n\nos.system('rm -rf ' + sys.argv[1])\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Introduce command injection vulnerability"], cwd=repo_dir, check=True)
    head_sha = (
        subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True)
        .stdout.strip()
    )

    return {"path": repo_dir, "base_sha": base_sha, "head_sha": head_sha}


@pytest.fixture
def e2e_client(monkeypatch, tmp_path):
    """Provide FastAPI test client configured with isolated SQLite DB and real DispatcherAuditProcessor."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", TEST_SECRET)

    db_file = tmp_path / "e2e_audits.db"
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

    # Real processor with local workspace provider
    workspace_provider = GitWorkspaceProvider(allow_local_repos=True)
    real_processor = DispatcherAuditProcessor(workspace_provider=workspace_provider)

    set_audit_processor(real_processor)
    set_session_provider(override_get_db)

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_audit_processor] = lambda: real_processor

    with TestClient(app) as client:
        client.session_factory = session_factory
        client.processor = real_processor
        yield client

    Base.metadata.drop_all(bind=engine)
    set_audit_processor(None)


class TestVerticalSliceEndToEnd:
    """Verifies complete vertical slice from webhook intake to persisted findings."""

    def test_full_webhook_to_static_analysis_success(self, e2e_client, local_vulnerable_repo):
        repo_path = local_vulnerable_repo["path"]
        base_sha = local_vulnerable_repo["base_sha"]
        head_sha = local_vulnerable_repo["head_sha"]

        payload = {
            "action": "opened",
            "number": 42,
            "repository": {
                "full_name": "thesis/sample-repo",
                "html_url": str(repo_path),
            },
            "pull_request": {
                "number": 42,
                "head": {"sha": head_sha},
                "base": {"sha": base_sha},
            },
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "delivery-e2e-001",
            "X-Hub-Signature-256": compute_signature(body_bytes),
        }

        # 1. Post webhook
        response = e2e_client.post("/api/v1/webhooks/github", content=body_bytes, headers=headers)
        assert response.status_code == 202
        resp_data = response.json()
        assert resp_data["status"] == "pending"
        audit_id = resp_data["audit_id"]

        # 2. Inspect persisted audit and findings (TestClient executes background tasks synchronously)
        session = e2e_client.session_factory()
        repo = AuditRepository(session)
        audit = repo.get_audit(audit_id)

        assert audit is not None
        assert audit.status == "completed"
        assert audit.head_commit == head_sha
        assert audit.base_commit == base_sha
        assert audit.pr_number == 42
        assert audit.duration_seconds is not None and audit.duration_seconds > 0
        assert audit.error_message is None
        assert audit.provenance.get("stage") == "static_only"
        assert audit.provenance.get("analyzed_head_commit") == head_sha
        assert audit.provenance.get("analyzed_base_commit") == base_sha

        # 3. Verify static findings persisted in database
        findings = repo.get_findings_for_audit(audit_id)
        assert len(findings) > 0

        # Assert finding attributes match Ruff/Semgrep CWE mappings
        vuln_findings = [f for f in findings if f.file_path == "vuln.py"]
        assert len(vuln_findings) > 0
        rule_codes = [f.provenance.get("rule_code") for f in vuln_findings if f.provenance]
        assert any(code in ("S605", "S607") for code in rule_codes if code) or any("S605" in f.title for f in vuln_findings)

        primary_cwes = [f.primary_cwe for f in vuln_findings]
        assert "CWE-78" in primary_cwes or "CWE-426" in primary_cwes

        session.close()

    def test_webhook_to_failed_audit_on_missing_commit(self, e2e_client, local_vulnerable_repo):
        repo_path = local_vulnerable_repo["path"]
        base_sha = local_vulnerable_repo["base_sha"]
        missing_head_sha = "1" * 40

        payload = {
            "action": "opened",
            "number": 99,
            "repository": {
                "full_name": "thesis/sample-repo",
                "html_url": str(repo_path),
            },
            "pull_request": {
                "number": 99,
                "head": {"sha": missing_head_sha},
                "base": {"sha": base_sha},
            },
        }
        body_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "delivery-e2e-fail",
            "X-Hub-Signature-256": compute_signature(body_bytes),
        }

        response = e2e_client.post("/api/v1/webhooks/github", content=body_bytes, headers=headers)
        assert response.status_code == 202
        audit_id = response.json()["audit_id"]

        session = e2e_client.session_factory()
        repo = AuditRepository(session)
        audit = repo.get_audit(audit_id)

        assert audit is not None
        assert audit.status == "failed"
        assert audit.error_message is not None
        assert "Diff acquisition failed" in audit.error_message
        assert missing_head_sha in audit.error_message

        # Findings should be empty
        findings = repo.get_findings_for_audit(audit_id)
        assert len(findings) == 0

        session.close()
