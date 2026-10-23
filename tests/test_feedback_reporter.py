"""Comprehensive offline unit and integration tests for GitHub PR Feedback Reporter."""

import json

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auditor.api.processor import DispatcherAuditProcessor
from auditor.db.models import Base, FindingRecord
from auditor.db.repository import AuditRepository
from auditor.feedback.reporter import (
    FeedbackResult,
    FeedbackStatus,
    GitHubPRFeedbackReporter,
    escape_markdown_table_cell,
    format_pr_summary_comment,
)


@pytest.fixture
def db_session(tmp_path):
    """Provide isolated in-memory or SQLite session for feedback tests."""
    db_file = tmp_path / "test_feedback.db"
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_audit(db_session):
    """Create a sample completed audit with repository and findings."""
    repo = AuditRepository(db_session)
    r = repo.get_or_create_repository(
        full_name="acme-corp/sample-backend",
        html_url="https://github.com/acme-corp/sample-backend",
    )
    audit = repo.create_audit(
        repository_id=r.id,
        request_id="req-sample-001",
        head_commit="a" * 40,
        base_commit="b" * 40,
        pr_number=42,
        configuration="A",
        provenance={"trigger": "test_fixture"},
    )
    audit.status = "completed"
    audit.duration_seconds = 3.14

    finding1 = FindingRecord(
        id="finding-001",
        audit_id=audit.id,
        detection_layer="deterministic_static",
        tool_name="ruff",
        category_id=2,
        primary_cwe="CWE-78",
        alternative_cwes=[],
        file_path="src/handlers/command.py",
        start_line=15,
        end_line=15,
        severity="high",
        confidence="high",
        title="OS Command Injection",
        description="Starting process with a shell: os.system(cmd)",
        suggestion="Use subprocess.run without shell=True",
        provenance={"rule_code": "S605"},
    )
    finding2 = FindingRecord(
        id="finding-002",
        audit_id=audit.id,
        detection_layer="deterministic_static",
        tool_name="semgrep",
        category_id=3,
        primary_cwe="CWE-89",
        alternative_cwes=[],
        file_path="src/db/queries.py",
        start_line=50,
        end_line=52,
        severity="medium",
        confidence="medium",
        title="SQL Injection Risk",
        description="Dynamic query formatting detected",
        suggestion="Use parameterized query",
        provenance={"rule_code": "python.security.sql-injection"},
    )
    db_session.add_all([finding1, finding2])
    db_session.commit()
    return audit


class TestMarkdownFormatting:
    """Test deterministic Markdown rendering and escaping."""

    def test_rendering_from_persisted_findings(self, sample_audit, db_session):
        repo = AuditRepository(db_session)
        findings = repo.get_findings_for_audit(sample_audit.id)
        body = format_pr_summary_comment(sample_audit, sample_audit.repository, findings)

        # Check marker
        assert f"<!-- AI_CODE_AUDITOR_REPORT:{sample_audit.id} -->" in body
        # Check header and metadata
        assert "## 🛡️ AI Code Auditor — Pull Request Audit Summary" in body
        assert "Config A" in body
        assert "✅ Completed" in body
        assert "3.14s" in body
        assert "a" * 40 in body
        assert "b" * 40 in body

        # Check severity counts
        assert "🔴 **High** | 1" in body
        assert "🟡 **Medium** | 1" in body
        assert "**Total Findings** | **2**" in body

        # Check finding entries
        assert "`S605` (CWE-78)" in body
        assert "`src/handlers/command.py:15`" in body
        assert "os.system(cmd)" in body
        assert "`python.security.sql-injection` (CWE-89)" in body

        # Check disclaimer note
        assert "Findings are currently reported on changed files" in body

    def test_audit_with_no_findings(self, sample_audit, db_session):
        body = format_pr_summary_comment(sample_audit, sample_audit.repository, [])
        assert "✅ **No security vulnerabilities or lint defects detected.**" in body
        assert "**Total Findings** | **0**" in body

    def test_failed_audit_rendering(self, sample_audit, db_session):
        sample_audit.status = "failed"
        sample_audit.error_message = "Clone timed out after 60s"
        body = format_pr_summary_comment(sample_audit, sample_audit.repository, [])
        assert "## ⚠️ AI Code Auditor — Audit Execution Failed" in body
        assert "Clone timed out after 60s" in body
        assert "Static analysis could not complete" in body

    def test_malformed_adversarial_content_escaping(self):
        raw = "Malformed | text with pipes\nand newlines\r\nand | | extra pipes"
        escaped = escape_markdown_table_cell(raw)
        assert "|" not in escaped.replace("\\|", "")
        assert "\n" not in escaped
        assert "\r" not in escaped

    def test_large_finding_sets_truncation(self, sample_audit, db_session):
        # Generate 60 findings
        findings = [
            FindingRecord(
                id=f"finding-bulk-{i:03d}",
                audit_id=sample_audit.id,
                detection_layer="deterministic_static",
                tool_name="ruff",
                category_id=1,
                primary_cwe="CWE-123",
                file_path=f"file_{i}.py",
                start_line=i,
                severity="low",
                confidence="low",
                title=f"Bulk finding {i}",
                description="Sample bulk violation",
                provenance={"rule_code": "F001"},
            )
            for i in range(60)
        ]
        body = format_pr_summary_comment(sample_audit, sample_audit.repository, findings, max_findings=10)
        assert "**Total Findings** | **60**" in body
        assert "*Note: Showing first 10 of 60 findings." in body
        # Only 10 finding rows rendered
        assert "`file_9.py:9`" in body
        assert "`file_10.py:10`" not in body


class TestFeedbackReporterOperations:
    """Test HTTP client operations, idempotency, updates, error handling, and security."""

    def test_feedback_disabled_by_default(self, sample_audit, db_session, monkeypatch):
        monkeypatch.delenv("GITHUB_FEEDBACK_ENABLED", raising=False)
        reporter = GitHubPRFeedbackReporter(token="mock-token")
        assert not reporter.enabled

        res = reporter.publish_audit_feedback(sample_audit.id, db_session)
        assert res.status == FeedbackStatus.DISABLED

        repo = AuditRepository(db_session)
        audit = repo.get_audit(sample_audit.id)
        assert audit.provenance.get("feedback", {}).get("status") == "disabled"
        assert audit.status == "completed"  # Audit status unchanged

    def test_missing_credentials(self, sample_audit, db_session, monkeypatch):
        monkeypatch.setenv("GITHUB_FEEDBACK_ENABLED", "true")
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        reporter = GitHubPRFeedbackReporter(enabled=True, token=None)

        res = reporter.publish_audit_feedback(sample_audit.id, db_session)
        assert res.status == FeedbackStatus.SKIPPED
        assert "GITHUB_TOKEN is not configured" in res.message

    def test_missing_pr_metadata(self, sample_audit, db_session):
        sample_audit.pr_number = None
        db_session.commit()

        reporter = GitHubPRFeedbackReporter(enabled=True, token="mock-token")
        res = reporter.publish_audit_feedback(sample_audit.id, db_session)
        assert res.status == FeedbackStatus.SKIPPED
        assert "no valid PR number" in res.message

    def test_successful_new_comment_creation(self, sample_audit, db_session):
        posted_requests = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            posted_requests.append(request)
            if request.method == "GET" and "/issues/42/comments" in str(request.url):
                # No existing comments
                return httpx.Response(200, json=[])
            elif request.method == "POST" and "/issues/42/comments" in str(request.url):
                body = json.loads(request.content)
                assert f"<!-- AI_CODE_AUDITOR_REPORT:{sample_audit.id} -->" in body["body"]
                return httpx.Response(201, json={"id": 98765, "body": body["body"]})
            return httpx.Response(404)

        transport = httpx.MockTransport(mock_handler)
        client = httpx.Client(transport=transport)
        reporter = GitHubPRFeedbackReporter(client=client, enabled=True, token="valid-test-token")

        res = reporter.publish_audit_feedback(sample_audit.id, db_session)
        assert res.status == FeedbackStatus.PUBLISHED
        assert res.comment_id == 98765

        # Check DB updated
        repo = AuditRepository(db_session)
        audit = repo.get_audit(sample_audit.id)
        assert audit.provenance["feedback"]["status"] == "published"
        assert audit.provenance["feedback"]["comment_id"] == 98765

    def test_update_existing_comment_idempotency(self, sample_audit, db_session):
        marker = f"<!-- AI_CODE_AUDITOR_REPORT:{sample_audit.id} -->"
        patched_requests = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET" and "/issues/42/comments" in str(request.url):
                # An existing comment with the marker already exists
                return httpx.Response(
                    200,
                    json=[
                        {"id": 11111, "body": "Hey please check this"},
                        {"id": 22222, "body": f"{marker}\nOld report content"},
                    ],
                )
            elif request.method == "PATCH" and "/issues/comments/22222" in str(request.url):
                patched_requests.append(request)
                body = json.loads(request.content)
                assert marker in body["body"]
                return httpx.Response(200, json={"id": 22222, "body": body["body"]})
            return httpx.Response(404)

        transport = httpx.MockTransport(mock_handler)
        client = httpx.Client(transport=transport)
        reporter = GitHubPRFeedbackReporter(client=client, enabled=True, token="valid-test-token")

        res = reporter.publish_audit_feedback(sample_audit.id, db_session)
        assert res.status == FeedbackStatus.UPDATED
        assert res.comment_id == 22222
        assert len(patched_requests) == 1

        repo = AuditRepository(db_session)
        audit = repo.get_audit(sample_audit.id)
        assert audit.provenance["feedback"]["status"] == "updated"
        assert audit.provenance["feedback"]["comment_id"] == 22222

    def test_recovery_when_local_persistence_failed_on_previous_run(self, sample_audit, db_session):
        # Simulation: GitHub accepted POST comment 55555 previously, but local DB didn't save it.
        marker = f"<!-- AI_CODE_AUDITOR_REPORT:{sample_audit.id} -->"
        audit_provenance = dict(sample_audit.provenance)
        audit_provenance.pop("feedback", None)  # No local record of comment
        sample_audit.provenance = audit_provenance
        db_session.commit()

        requests_log = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            requests_log.append(request.method)
            if request.method == "GET":
                return httpx.Response(200, json=[{"id": 55555, "body": f"{marker}\nPrior accepted comment"}])
            elif request.method == "PATCH" and "/issues/comments/55555" in str(request.url):
                return httpx.Response(200, json={"id": 55555})
            return httpx.Response(404)

        transport = httpx.MockTransport(mock_handler)
        client = httpx.Client(transport=transport)
        reporter = GitHubPRFeedbackReporter(client=client, enabled=True, token="test-token")

        # Retry publishing
        res = reporter.publish_audit_feedback(sample_audit.id, db_session)
        assert res.status == FeedbackStatus.UPDATED
        assert res.comment_id == 55555
        assert "POST" not in requests_log  # Did not duplicate!
        assert "PATCH" in requests_log

    def test_http_auth_permission_failure_handling(self, sample_audit, db_session):
        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, json={"message": "Resource not accessible by integration"})

        transport = httpx.MockTransport(mock_handler)
        client = httpx.Client(transport=transport)
        reporter = GitHubPRFeedbackReporter(client=client, enabled=True, token="token-403")

        res = reporter.publish_audit_feedback(sample_audit.id, db_session)
        assert res.status == FeedbackStatus.FAILED
        assert "403" in res.error

        # Ensure audit record in DB remains completed!
        repo = AuditRepository(db_session)
        audit = repo.get_audit(sample_audit.id)
        assert audit.status == "completed"
        assert audit.provenance["feedback"]["status"] == "failed"

    def test_api_timeout_handling(self, sample_audit, db_session):
        def mock_handler(request: httpx.Request):
            raise httpx.TimeoutException("Read timed out after 15s")

        transport = httpx.MockTransport(mock_handler)
        client = httpx.Client(transport=transport)
        reporter = GitHubPRFeedbackReporter(client=client, enabled=True, token="test-token")

        res = reporter.publish_audit_feedback(sample_audit.id, db_session)
        assert res.status == FeedbackStatus.FAILED
        assert "timed out" in res.error

        repo = AuditRepository(db_session)
        audit = repo.get_audit(sample_audit.id)
        assert audit.status == "completed"

    def test_token_redaction_in_errors(self, sample_audit, db_session):
        sensitive_token = "ghp_super_secret_token_12345"

        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                401,
                json={"message": f"Bad credentials with token {sensitive_token} and Bearer {sensitive_token}"},
            )

        transport = httpx.MockTransport(mock_handler)
        client = httpx.Client(transport=transport)
        reporter = GitHubPRFeedbackReporter(client=client, enabled=True, token=sensitive_token)

        res = reporter.publish_audit_feedback(sample_audit.id, db_session)
        assert res.status == FeedbackStatus.FAILED
        assert sensitive_token not in res.error
        assert "[REDACTED]" in res.error

    def test_rate_limit_and_server_error_handling(self, sample_audit, db_session):
        # 429 Rate Limit
        def rate_limit_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"message": "API rate limit exceeded"})

        reporter_429 = GitHubPRFeedbackReporter(
            client=httpx.Client(transport=httpx.MockTransport(rate_limit_handler)),
            enabled=True,
            token="test-token",
        )
        res_429 = reporter_429.publish_audit_feedback(sample_audit.id, db_session)
        assert res_429.status == FeedbackStatus.FAILED
        assert "429" in res_429.error

        # 500 Internal Server Error
        def server_error_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"message": "Internal Server Error"})

        reporter_500 = GitHubPRFeedbackReporter(
            client=httpx.Client(transport=httpx.MockTransport(server_error_handler)),
            enabled=True,
            token="test-token",
        )
        res_500 = reporter_500.publish_audit_feedback(sample_audit.id, db_session)
        assert res_500.status == FeedbackStatus.FAILED
        assert "500" in res_500.error

    def test_invalid_repository_ssrf_rejection(self, sample_audit, db_session):
        sample_audit.repository.full_name = "evil.com/attacker/repo; rm -rf"
        db_session.commit()

        reporter = GitHubPRFeedbackReporter(enabled=True, token="valid-token")
        res = reporter.publish_audit_feedback(sample_audit.id, db_session)
        assert res.status == FeedbackStatus.FAILED
        assert "forbidden characters" in res.error or "Unsupported repository" in res.error


class TestProcessorPipelineIntegration:
    """Test full integration with DispatcherAuditProcessor."""

    def test_processor_executes_reporter_after_commit(self, db_session, tmp_path):
        repo = AuditRepository(db_session)
        r = repo.get_or_create_repository("org/repo")
        audit = repo.create_audit(
            repository_id=r.id,
            request_id="proc-test-req-001",
            head_commit="f" * 40,
            base_commit="e" * 40,
            pr_number=77,
            configuration="A",
            provenance={"workspace_path": str(tmp_path)},
        )
        db_session.commit()

        called_audits = []

        class SpyReporter:
            def publish_audit_feedback(self, audit_id: str, session):
                called_audits.append(audit_id)
                # Verify audit is already committed before feedback
                a = repo.get_audit(audit_id)
                assert a.status == "completed" or a.status == "failed"
                return FeedbackResult(status=FeedbackStatus.PUBLISHED, comment_id=4444)

        # Mock dispatcher to return success
        from auditor.models.config import AuditConfiguration
        from auditor.models.result import AuditRunResult, AuditStatus

        class FakeDispatcher:
            diff_provider = None

            def dispatch(self, req):
                return AuditRunResult(
                    run_id="run-fake",
                    request_id=req.request_id,
                    configuration=AuditConfiguration.A,
                    status=AuditStatus.SUCCESS,
                    findings=[],
                )

        spy = SpyReporter()
        proc = DispatcherAuditProcessor(dispatcher=FakeDispatcher(), feedback_reporter=spy)
        proc.process_audit(audit.id, db_session)

        assert audit.id in called_audits
        updated = repo.get_audit(audit.id)
        assert updated.status == "completed"

    def test_processor_preserves_completed_status_when_reporter_crashes(self, db_session, tmp_path):
        repo = AuditRepository(db_session)
        r = repo.get_or_create_repository("org/repo")
        audit = repo.create_audit(
            repository_id=r.id,
            request_id="proc-crash-req-002",
            head_commit="f" * 40,
            pr_number=88,
            configuration="A",
            provenance={"workspace_path": str(tmp_path)},
        )
        db_session.commit()

        class ExplodingReporter:
            def publish_audit_feedback(self, audit_id: str, session):
                raise RuntimeError("Catastrophic reporter network failure")

        from auditor.models.config import AuditConfiguration
        from auditor.models.result import AuditRunResult, AuditStatus

        class FakeDispatcher:
            diff_provider = None

            def dispatch(self, req):
                return AuditRunResult(
                    run_id="run-fake-2",
                    request_id=req.request_id,
                    configuration=AuditConfiguration.A,
                    status=AuditStatus.SUCCESS,
                    findings=[],
                )

        proc = DispatcherAuditProcessor(dispatcher=FakeDispatcher(), feedback_reporter=ExplodingReporter())
        # Should not raise exception
        proc.process_audit(audit.id, db_session)

        updated = repo.get_audit(audit.id)
        # Audit remains completed despite feedback crash!
        assert updated.status == "completed"


class TestReporterPagination:
    """Tests for GitHub comment discovery pagination and safety bounds."""

    def test_discovery_follows_link_header_pagination(self, sample_audit, db_session):
        audit_id = sample_audit.id
        marker = f"<!-- AI_CODE_AUDITOR_REPORT:{audit_id} -->"

        page2_url = "https://api.github.com/repos/acme-corp/sample-backend/issues/42/comments?per_page=100&page=2"

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url)
            if "page=2" in url_str:
                # Page 2 has the comment with the marker
                body = [{"id": 999222, "body": f"Older review comment\n{marker}"}]
                return httpx.Response(200, json=body)
            elif request.method == "GET" and "/comments" in url_str:
                # Page 1 has 100 other comments and a Link header pointing to page 2
                body = [{"id": 1000 + i, "body": f"Comment {i}"} for i in range(100)]
                headers = {"Link": f'<{page2_url}>; rel="next"'}
                return httpx.Response(200, json=body, headers=headers)
            elif request.method == "PATCH" and "999222" in url_str:
                return httpx.Response(200, json={"id": 999222, "body": "updated"})
            return httpx.Response(404, json={})

        transport = httpx.MockTransport(mock_handler)
        client = httpx.Client(transport=transport)
        reporter = GitHubPRFeedbackReporter(client=client, enabled=True, token="ghp_test")

        res = reporter.publish_audit_feedback(audit_id, db_session)
        assert res.status == FeedbackStatus.UPDATED
        assert res.comment_id == 999222

    def test_discovery_safety_limit_marks_incomplete(self, sample_audit, db_session):
        audit_id = sample_audit.id

        def mock_handler(request: httpx.Request) -> httpx.Response:
            if request.method == "GET" and "/comments" in str(request.url):
                # Return 100 comments on every page with Link to next page, never containing the marker
                headers = {"Link": '<https://api.github.com/repos/acme-corp/sample-backend/issues/42/comments?page=next>; rel="next"'}
                return httpx.Response(200, json=[{"id": 1, "body": "noise"} for _ in range(100)], headers=headers)
            elif request.method == "POST":
                return httpx.Response(201, json={"id": 888111, "body": "created"})
            return httpx.Response(404, json={})

        transport = httpx.MockTransport(mock_handler)
        client = httpx.Client(transport=transport)
        # Set tight max_discovery_pages limit of 2 pages
        reporter = GitHubPRFeedbackReporter(
            client=client, enabled=True, token="ghp_test", max_discovery_pages=2
        )

        res = reporter.publish_audit_feedback(audit_id, db_session)
        assert res.status == FeedbackStatus.PUBLISHED

        repo = AuditRepository(db_session)
        updated = repo.get_audit(audit_id)
        # Audit provenance must record that discovery was incomplete due to safety limit
        prov = updated.provenance or {}
        assert prov.get("feedback", {}).get("discovery_search_incomplete") is True
        assert prov.get("feedback", {}).get("discovery_pages_scanned") == 2

