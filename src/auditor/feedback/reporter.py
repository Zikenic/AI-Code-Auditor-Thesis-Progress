"""GitHub Pull Request Feedback Reporter.

Publishes deterministic, idempotent audit summary comments on target GitHub Pull Requests
using GitHub's Issue Comments REST API.
"""

from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import httpx
from sqlalchemy.orm import Session

from auditor.db.models import AuditRecord, FindingRecord, RepositoryRecord
from auditor.db.repository import AuditRepository
from auditor.orchestration.git_provider import _sanitize_error_text, validate_repository

logger = logging.getLogger(__name__)

REPORT_MARKER_PREFIX = "<!-- AI_CODE_AUDITOR_REPORT:"
DEFAULT_MAX_FINDINGS_IN_COMMENT = 50
DEFAULT_MAX_DISCOVERY_PAGES = 20


class FeedbackStatus(StrEnum):
    """Publication outcome status."""

    PUBLISHED = "published"
    UPDATED = "updated"
    SKIPPED = "skipped"
    DISABLED = "disabled"
    FAILED = "failed"


@dataclass(frozen=True)
class FeedbackResult:
    """Outcome of attempting to publish feedback to GitHub."""

    status: FeedbackStatus
    comment_id: int | None = None
    message: str = ""
    error: str | None = None


def _sanitize_reporter_error(text: str, token: str | None = None) -> str:
    """Sanitize reporter errors, scrubbing custom token, env token, and token patterns."""
    if token:
        text = text.replace(token, "[REDACTED]")
    # Scrub common GitHub token prefixes
    text = re.sub(r"ghp_[a-zA-Z0-9_]+", "[REDACTED]", text)
    text = re.sub(r"github_pat_[a-zA-Z0-9_]+", "[REDACTED]", text)
    text = re.sub(r"gho_[a-zA-Z0-9_]+", "[REDACTED]", text)
    return _sanitize_error_text(text)


def escape_markdown_table_cell(text: str | None) -> str:
    """Escape pipes, newlines, and unformatted characters for safe inclusion in Markdown table cells."""
    if not text:
        return "N/A"
    cleaned = text.replace("|", "\\|").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return cleaned.strip()


def format_pr_summary_comment(
    audit: AuditRecord,
    repository: RepositoryRecord,
    findings: list[FindingRecord],
    max_findings: int = DEFAULT_MAX_FINDINGS_IN_COMMENT,
) -> str:
    """Construct deterministic Markdown audit summary comment with embedded idempotency marker."""
    marker = f"{REPORT_MARKER_PREFIX}{audit.id} -->"
    is_failed = audit.status == "failed"

    lines: list[str] = [marker]

    if is_failed:
        lines.extend([
            "## ⚠️ AI Code Auditor — Audit Execution Failed",
            "",
            "The automated audit for this pull request encountered an execution failure:",
            f"> {_sanitize_error_text(audit.error_message or 'Unknown pipeline failure')}",
            "",
            "### 📋 Audit Coordinates",
            "| Parameter | Value |",
            "| :--- | :--- |",
            f"| **Audit ID** | `{audit.id}` |",
            f"| **Configuration** | **Config {audit.configuration}** |",
            f"| **Head Commit** | `{audit.head_commit}` |",
            f"| **Base Commit** | `{audit.base_commit or 'N/A'}` |",
            "",
            "> [!CAUTION]",
            "> Static analysis could not complete. Please check the pipeline logs or retry the audit.",
        ])
        return "\n".join(lines)

    # Completed or Partial Audit Header
    cfg_desc_map = {
        "A": "Config A (Static Analysis Baseline)",
        "B": "Config B (LLM Code Review Only)",
        "C": "Config C (Hybrid Static Analysis + LLM Review)",
        "D": "Config D (Full Hybrid with Repo Context)",
    }
    cfg_label = cfg_desc_map.get(str(audit.configuration).upper(), f"Config {audit.configuration}")

    lines.extend([
        "## 🛡️ AI Code Auditor — Pull Request Audit Summary",
        "",
        "| Parameter | Value |",
        "| :--- | :--- |",
        f"| **Audit ID** | `{audit.id}` |",
        f"| **Configuration** | **{cfg_label}** |",
        f"| **Status** | {'✅ Completed' if audit.status == 'completed' else '🟡 ' + audit.status.capitalize()} |",
        f"| **Duration** | {f'{audit.duration_seconds:.2f}s' if audit.duration_seconds is not None else 'N/A'} |",
        f"| **Head Commit** | `{audit.head_commit}` |",
        f"| **Base Commit** | `{audit.base_commit or 'N/A'}` |",
        "",
    ])

    # Severity Counts
    high_count = sum(1 for f in findings if f.severity.lower() == "high")
    med_count = sum(1 for f in findings if f.severity.lower() == "medium")
    low_count = sum(1 for f in findings if f.severity.lower() == "low")
    info_count = sum(1 for f in findings if f.severity.lower() in ("info", "informational"))
    total_count = len(findings)

    lines.extend([
        "### 📊 Summary of Findings",
        "",
        "| Severity | Count |",
        "| :--- | :--- |",
        f"| 🔴 **High** | {high_count} |",
        f"| 🟡 **Medium** | {med_count} |",
        f"| 🔵 **Low** | {low_count} |",
    ])
    if info_count > 0:
        lines.append(f"| ⚪ **Informational** | {info_count} |")
    lines.extend([
        f"| **Total Findings** | **{total_count}** |",
        "",
    ])

    # Hybrid Triage Breakdown if present or if Config C
    confirmed_count = sum(1 for f in findings if (f.provenance or {}).get("triage") == "confirmed")
    fp_count = sum(1 for f in findings if (f.provenance or {}).get("triage") == "likely_false_positive")
    inconclusive_count = sum(1 for f in findings if (f.provenance or {}).get("triage") == "inconclusive")
    llm_additional_count = sum(1 for f in findings if getattr(f, "detection_layer", "") == "heuristic_llm")
    has_triage = (
        confirmed_count > 0
        or fp_count > 0
        or inconclusive_count > 0
        or llm_additional_count > 0
        or str(audit.configuration).upper() == "C"
    )

    if has_triage:
        lines.extend([
            "### 🤖 LLM Triage & Hybrid Review Breakdown",
            "",
            "| Review Classification | Count |",
            "| :--- | :--- |",
            f"| 🟢 **Confirmed Static Findings** | {confirmed_count} |",
            f"| ⚪ **Triaged Likely False Positives** | {fp_count} |",
            f"| ❓ **Inconclusive Findings** | {inconclusive_count} |",
        ])
        if llm_additional_count > 0:
            lines.append(f"| 🔍 **Additional LLM-Detected Findings** | {llm_additional_count} |")
        lines.append("")

    # Findings Detail Table
    lines.append("### 🔍 Detailed Findings")
    lines.append("")

    if total_count == 0:
        lines.append("✅ **No security vulnerabilities or lint defects detected.**")
    else:
        lines.extend([
            "| Severity | Rule / CWE | Location | Description |",
            "| :--- | :--- | :--- | :--- |",
        ])

        displayed_findings = findings[:max_findings]
        for f in displayed_findings:
            sev_badge = {
                "high": "🔴 High",
                "medium": "🟡 Medium",
                "low": "🔵 Low",
            }.get(f.severity.lower(), f.severity.capitalize())

            rule_code = f.provenance.get("rule_code") or f.provenance.get("rule_id") or f.tool_name
            rule_cwe_text = f"`{rule_code}` ({f.primary_cwe})"

            loc = f"`{f.file_path}:{f.start_line}`" if f.start_line is not None else f"`{f.file_path}`"

            # Triage badge prefix in description
            triage_val = (f.provenance or {}).get("triage")
            triage_prefix = ""
            if triage_val == "confirmed":
                triage_prefix = "[Confirmed] "
            elif triage_val == "likely_false_positive":
                triage_prefix = "[Likely FP] "
            elif triage_val == "inconclusive":
                triage_prefix = "[Inconclusive] "
            elif getattr(f, "detection_layer", "") == "heuristic_llm":
                triage_prefix = "[LLM Review] "

            raw_desc = f.description or f.title
            clean_desc = escape_markdown_table_cell(f"{triage_prefix}{raw_desc}")
            # Truncate overly verbose descriptions to keep table readable
            if len(clean_desc) > 200:
                clean_desc = clean_desc[:197] + "..."

            lines.append(f"| {sev_badge} | {rule_cwe_text} | {loc} | {clean_desc} |")

        if total_count > max_findings:
            lines.extend([
                "",
                f"*Note: Showing first {max_findings} of {total_count} findings. "
                "Full results are recorded in the persistent audit database.*",
            ])

    lines.extend([
        "",
        "> [!NOTE]",
        "> Findings are currently reported on changed files and may include pre-existing issues on unchanged lines within those files.",
    ])

    return "\n".join(lines)


class IFeedbackReporter(ABC):
    """Abstract interface for audit feedback reporting components."""

    @abstractmethod
    def publish_audit_feedback(self, audit_id: str, session: Session) -> FeedbackResult:
        """Publish or update audit feedback on the collaboration platform."""
        pass


class GitHubPRFeedbackReporter(IFeedbackReporter):
    """Publishes idempotent audit summary comments to GitHub Pull Requests."""

    def __init__(
        self,
        client: httpx.Client | None = None,
        enabled: bool | None = None,
        token: str | None = None,
        base_url: str = "https://api.github.com",
        timeout_seconds: float = 15.0,
        max_findings_per_comment: int = DEFAULT_MAX_FINDINGS_IN_COMMENT,
        max_discovery_pages: int = DEFAULT_MAX_DISCOVERY_PAGES,
    ):
        self._custom_client = client
        self.enabled = (
            enabled
            if enabled is not None
            else os.environ.get("GITHUB_FEEDBACK_ENABLED", "").lower() in ("true", "1", "yes")
        )
        self.token = token if token is not None else os.environ.get("GITHUB_TOKEN")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_findings = max_findings_per_comment
        self.max_discovery_pages = max_discovery_pages

    def _get_client(self) -> httpx.Client:
        """Return injected HTTP client or create an isolated, secure instance."""
        if self._custom_client is not None:
            return self._custom_client
        return httpx.Client(
            timeout=self.timeout_seconds,
            verify=True,
            follow_redirects=False,
        )

    def publish_audit_feedback(self, audit_id: str, session: Session) -> FeedbackResult:
        """Publish or update PR audit summary comment idempotently."""
        repo = AuditRepository(session)
        audit = repo.get_audit(audit_id)
        if not audit:
            logger.error("Cannot publish feedback: Audit %s not found.", audit_id)
            return FeedbackResult(
                status=FeedbackStatus.FAILED,
                error=f"Audit {audit_id} not found in database.",
            )

        # 1. Safe default check: Feedback posting must be explicitly enabled
        if not self.enabled:
            logger.info("GitHub PR feedback is disabled via GITHUB_FEEDBACK_ENABLED for audit %s.", audit_id)
            repo.record_feedback_result(audit_id, feedback_status=FeedbackStatus.DISABLED.value)
            session.commit()
            return FeedbackResult(
                status=FeedbackStatus.DISABLED,
                message="Feedback posting is disabled via GITHUB_FEEDBACK_ENABLED.",
            )

        # 2. Check for missing authentication credential
        if not self.token or not self.token.strip():
            logger.info("GitHub feedback posting skipped: GITHUB_TOKEN not configured for audit %s.", audit_id)
            repo.record_feedback_result(
                audit_id,
                feedback_status=FeedbackStatus.SKIPPED.value,
                error="GITHUB_TOKEN not configured.",
            )
            session.commit()
            return FeedbackResult(
                status=FeedbackStatus.SKIPPED,
                message="GITHUB_TOKEN is not configured.",
            )

        # 3. Check for Pull Request number association
        if audit.pr_number is None or audit.pr_number <= 0:
            logger.info("GitHub feedback posting skipped: Audit %s has no valid PR number.", audit_id)
            repo.record_feedback_result(
                audit_id,
                feedback_status=FeedbackStatus.SKIPPED.value,
                error="Audit has no valid PR number.",
            )
            session.commit()
            return FeedbackResult(
                status=FeedbackStatus.SKIPPED,
                message="Audit has no valid PR number.",
            )

        # 4. Check repository coordinates
        repository = audit.repository
        if not repository or not repository.full_name or "/" not in repository.full_name:
            logger.warning("GitHub feedback posting skipped: Invalid repository metadata for audit %s.", audit_id)
            repo.record_feedback_result(
                audit_id,
                feedback_status=FeedbackStatus.SKIPPED.value,
                error="Missing or invalid repository coordinates.",
            )
            session.commit()
            return FeedbackResult(
                status=FeedbackStatus.SKIPPED,
                message="Missing or invalid repository coordinates.",
            )

        # Validate repository format to prevent SSRF / arbitrary host redirection
        try:
            validate_repository(repository.full_name, allow_local_repos=False)
        except Exception as val_err:
            sanitized = _sanitize_reporter_error(str(val_err), token=self.token)
            repo.record_feedback_result(
                audit_id,
                feedback_status=FeedbackStatus.FAILED.value,
                error=sanitized,
            )
            session.commit()
            return FeedbackResult(status=FeedbackStatus.FAILED, error=sanitized)

        owner, repo_name = repository.full_name.split("/", 1)
        pr_number = audit.pr_number

        # 5. Retrieve findings and format Markdown comment
        findings = repo.get_findings_for_audit(audit_id)
        comment_body = format_pr_summary_comment(
            audit=audit,
            repository=repository,
            findings=findings,
            max_findings=self.max_findings,
        )

        marker = f"{REPORT_MARKER_PREFIX}{audit.id} -->"
        headers = {
            "Authorization": f"Bearer {self.token.strip()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "AI-Code-Auditor",
        }

        client = self._get_client()

        # 6. Idempotency: Locate existing comment with this audit's marker
        existing_comment_id = (audit.provenance or {}).get("feedback", {}).get("comment_id")

        if not existing_comment_id:
            try:
                pages_scanned = 0
                next_url: str | None = f"{self.base_url}/repos/{owner}/{repo_name}/issues/{pr_number}/comments"
                request_params: dict[str, Any] | None = {"per_page": 100}

                while next_url and pages_scanned < self.max_discovery_pages:
                    pages_scanned += 1
                    res = client.get(next_url, headers=headers, params=request_params)
                    # Once initial query is issued, subsequent pagination URLs from Link header contain query parameters
                    request_params = None

                    if res.status_code == 200:
                        comments = res.json()
                        if isinstance(comments, list):
                            for c in comments:
                                if marker in (c.get("body") or ""):
                                    existing_comment_id = c.get("id")
                                    logger.info(
                                        "Discovered existing report comment %s on PR #%s for audit %s",
                                        existing_comment_id,
                                        pr_number,
                                        audit_id,
                                    )
                                    break
                            if existing_comment_id:
                                break

                        # Check RFC 5988 Link header for rel="next"
                        next_link = res.links.get("next")
                        if next_link and "url" in next_link:
                            next_url = next_link["url"]
                        elif isinstance(comments, list) and len(comments) == 100:
                            # Fallback page increment if Link header omitted by proxy/mock
                            page = pages_scanned + 1
                            next_url = f"{self.base_url}/repos/{owner}/{repo_name}/issues/{pr_number}/comments?per_page=100&page={page}"
                        else:
                            next_url = None
                    elif res.status_code in (401, 403, 404):
                        err_text = _sanitize_reporter_error(f"GitHub API {res.status_code}: {res.text}", token=self.token)
                        repo.record_feedback_result(
                            audit_id,
                            feedback_status=FeedbackStatus.FAILED.value,
                            error=err_text,
                        )
                        session.commit()
                        return FeedbackResult(status=FeedbackStatus.FAILED, error=err_text)
                    else:
                        break

                if not existing_comment_id and next_url and pages_scanned >= self.max_discovery_pages:
                    logger.warning(
                        "Comment discovery reached safety limit of %d pages for audit %s; search is incomplete.",
                        pages_scanned,
                        audit_id,
                    )
                    prov = dict(audit.provenance or {})
                    fb_prov = prov.setdefault("feedback", {})
                    fb_prov["discovery_search_incomplete"] = True
                    fb_prov["discovery_pages_scanned"] = pages_scanned
                    audit.provenance = prov
                    session.commit()
            except Exception as e:
                err_text = _sanitize_reporter_error(
                    f"Network error discovering existing comments: {str(e)}", token=self.token
                )
                repo.record_feedback_result(
                    audit_id,
                    feedback_status=FeedbackStatus.FAILED.value,
                    error=err_text,
                )
                session.commit()
                return FeedbackResult(status=FeedbackStatus.FAILED, error=err_text)

        # 7. Post new comment or Patch existing comment
        try:
            if existing_comment_id:
                # Update existing comment
                update_url = f"{self.base_url}/repos/{owner}/{repo_name}/issues/comments/{existing_comment_id}"
                patch_res = client.patch(update_url, headers=headers, json={"body": comment_body})
                if patch_res.status_code == 200:
                    repo.record_feedback_result(
                        audit_id,
                        feedback_status=FeedbackStatus.UPDATED.value,
                        comment_id=existing_comment_id,
                    )
                    session.commit()
                    return FeedbackResult(
                        status=FeedbackStatus.UPDATED,
                        comment_id=existing_comment_id,
                        message=f"Updated existing PR comment {existing_comment_id}.",
                    )
                elif patch_res.status_code == 404:
                    # Comment was deleted remotely; fallback to creating new comment
                    logger.warning(
                        "Comment %s not found on GitHub (deleted?). Recreating comment for audit %s.",
                        existing_comment_id,
                        audit_id,
                    )
                    existing_comment_id = None
                else:
                    err_text = _sanitize_reporter_error(
                        f"GitHub API PATCH comment failed ({patch_res.status_code}): {patch_res.text}",
                        token=self.token,
                    )
                    repo.record_feedback_result(
                        audit_id,
                        feedback_status=FeedbackStatus.FAILED.value,
                        comment_id=existing_comment_id,
                        error=err_text,
                    )
                    session.commit()
                    return FeedbackResult(
                        status=FeedbackStatus.FAILED,
                        comment_id=existing_comment_id,
                        error=err_text,
                    )

            if not existing_comment_id:
                # Create new comment
                create_url = f"{self.base_url}/repos/{owner}/{repo_name}/issues/{pr_number}/comments"
                post_res = client.post(create_url, headers=headers, json={"body": comment_body})
                if post_res.status_code == 201:
                    new_comment_id = post_res.json().get("id")
                    repo.record_feedback_result(
                        audit_id,
                        feedback_status=FeedbackStatus.PUBLISHED.value,
                        comment_id=new_comment_id,
                    )
                    session.commit()
                    return FeedbackResult(
                        status=FeedbackStatus.PUBLISHED,
                        comment_id=new_comment_id,
                        message=f"Published new PR comment {new_comment_id}.",
                    )
                else:
                    err_text = _sanitize_reporter_error(
                        f"GitHub API POST comment failed ({post_res.status_code}): {post_res.text}",
                        token=self.token,
                    )
                    repo.record_feedback_result(
                        audit_id,
                        feedback_status=FeedbackStatus.FAILED.value,
                        error=err_text,
                    )
                    session.commit()
                    return FeedbackResult(status=FeedbackStatus.FAILED, error=err_text)

        except Exception as e:
            err_text = _sanitize_reporter_error(
                f"Network error publishing PR feedback: {str(e)}", token=self.token
            )
            logger.exception("GitHub comment publishing network error for audit %s: %s", audit_id, err_text)
            repo.record_feedback_result(
                audit_id,
                feedback_status=FeedbackStatus.FAILED.value,
                comment_id=existing_comment_id,
                error=err_text,
            )
            session.commit()
            return FeedbackResult(
                status=FeedbackStatus.FAILED,
                comment_id=existing_comment_id,
                error=err_text,
            )

        return FeedbackResult(status=FeedbackStatus.FAILED, error="Unhandled execution path.")
