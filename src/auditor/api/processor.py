"""Audit processor abstraction bridging webhook intake with dispatcher execution."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path

from sqlalchemy.orm import Session

from auditor.db.repository import AuditRepository
from auditor.feedback.reporter import GitHubPRFeedbackReporter, IFeedbackReporter
from auditor.models.config import AuditConfiguration
from auditor.models.request import AuditRequest
from auditor.models.result import AuditRunResult, AuditStatus
from auditor.orchestration.dispatcher import ConfigurationDispatcher
from auditor.orchestration.git_provider import (
    GitWorkspaceProvider,
    PrecomputedDiffProvider,
    _sanitize_error_text,
)
from auditor.orchestration.interfaces import UnimplementedDiffProvider

logger = logging.getLogger(__name__)


class IAuditProcessor(ABC):
    """Abstract processing interface for executing enqueued audits."""

    @abstractmethod
    def process_audit(self, audit_id: str, session: Session) -> None:
        """Execute audit processing for the designated audit record."""
        pass


class DispatcherAuditProcessor(IAuditProcessor):
    """Processes enqueued audits using Git workspace materialization and ConfigurationDispatcher.

    Acquires PR source and diff via GitWorkspaceProvider, dispatches analysis to
    ConfigurationDispatcher, and persists findings and final audit status.
    Guarantees isolation and resource cleanup on success and failure.
    """

    def __init__(
        self,
        dispatcher: ConfigurationDispatcher | None = None,
        workspace_provider: GitWorkspaceProvider | None = None,
        feedback_reporter: IFeedbackReporter | None = None,
    ):
        self.dispatcher = dispatcher or ConfigurationDispatcher()
        self.workspace_provider = workspace_provider or GitWorkspaceProvider()
        self.feedback_reporter = feedback_reporter or GitHubPRFeedbackReporter()

    def process_audit(self, audit_id: str, session: Session) -> None:
        start_time = time.monotonic()
        repo = AuditRepository(session)
        audit = repo.get_audit(audit_id)
        if not audit:
            logger.error("Audit not found for processing: %s", audit_id)
            return

        # 1. Transition status to running
        repo.update_audit_status(audit_id, status="running")
        session.commit()

        try:
            # 2. Map DB record to domain AuditRequest configuration
            try:
                cfg = AuditConfiguration(audit.configuration)
            except ValueError:
                cfg = AuditConfiguration.A

            # Check if an existing/pre-allocated workspace path was provided
            existing_ws = audit.provenance.get("workspace_path") if audit.provenance else None

            if existing_ws and Path(existing_ws).is_dir():
                audit_req = AuditRequest(
                    request_id=audit.request_id,
                    repository_id=audit.repository.full_name if audit.repository else "unknown",
                    pr_number=audit.pr_number,
                    head_commit=audit.head_commit,
                    base_commit=audit.base_commit,
                    configuration=cfg,
                    workspace_path=str(existing_ws),
                )
                result: AuditRunResult = self.dispatcher.dispatch(audit_req)
            else:
                # 3. Materialize isolated PR workspace and extract diff
                repo_target = (
                    audit.repository.html_url
                    or (audit.repository.full_name if audit.repository else None)
                )
                if not repo_target:
                    raise ValueError(f"Audit record {audit_id} has no repository coordinates.")

                with self.workspace_provider.materialize(
                    repository_id=repo_target,
                    head_commit=audit.head_commit,
                    base_commit=audit.base_commit,
                    pr_number=audit.pr_number,
                ) as ws:
                    audit_req = AuditRequest(
                        request_id=audit.request_id,
                        repository_id=audit.repository.full_name if audit.repository else "unknown",
                        pr_number=audit.pr_number,
                        head_commit=audit.head_commit,
                        base_commit=audit.base_commit,
                        configuration=cfg,
                        workspace_path=str(ws.workspace_path),
                    )

                    # Provide precomputed diff to dispatcher if none is explicitly configured
                    original_diff_provider = self.dispatcher.diff_provider
                    if isinstance(original_diff_provider, UnimplementedDiffProvider):
                        self.dispatcher.diff_provider = PrecomputedDiffProvider(
                            ws.diff_content, ws.changed_files
                        )

                    try:
                        result = self.dispatcher.dispatch(audit_req)
                    finally:
                        self.dispatcher.diff_provider = original_diff_provider

            # 4. Map and persist result
            status_map = {
                AuditStatus.SUCCESS: "completed",
                AuditStatus.PARTIAL: "partial",
                AuditStatus.FAILED: "failed",
            }
            final_status = status_map.get(result.status, "failed")
            duration = round(time.monotonic() - start_time, 3)

            provenance = dict(audit.provenance or {})
            if result.provenance:
                provenance.update(result.provenance)
            provenance["analyzed_head_commit"] = audit.head_commit
            provenance["analyzed_base_commit"] = audit.base_commit

            repo.update_audit_status(
                audit_id=audit_id,
                status=final_status,
                duration_seconds=duration,
                error_message=result.error_message,
                provenance=provenance,
            )

            if result.findings:
                repo.persist_findings(audit_id, result.findings)

            session.commit()

            # 5. Publish PR feedback summary comment if enabled
            if self.feedback_reporter:
                try:
                    self.feedback_reporter.publish_audit_feedback(audit_id, session)
                except Exception as fb_err:
                    logger.warning("Feedback publication error for audit %s: %s", audit_id, fb_err)

        except Exception as e:
            duration = round(time.monotonic() - start_time, 3)
            logger.exception("Audit background execution failed for %s: %s", audit_id, str(e))
            sanitized_err = _sanitize_error_text(str(e))
            if "Diff acquisition failed" not in sanitized_err:
                error_message = f"Diff acquisition failed: {sanitized_err}"
            else:
                error_message = sanitized_err

            repo.update_audit_status(
                audit_id=audit_id,
                status="failed",
                duration_seconds=duration,
                error_message=error_message,
            )
            session.commit()
