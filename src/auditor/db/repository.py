"""Repository and CRUD operations for audit entities."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from auditor.db.models import AuditRecord, FindingRecord, RepositoryRecord
from auditor.models.finding import PredictedFinding


class AuditRepository:
    """Encapsulates transactional CRUD operations for repositories, audits, and findings."""

    def __init__(self, session: Session):
        self.session = session

    def get_or_create_repository(
        self,
        full_name: str,
        html_url: str | None = None,
    ) -> RepositoryRecord:
        """Retrieve existing repository record or create a new one."""
        stmt = select(RepositoryRecord).where(RepositoryRecord.full_name == full_name)
        repo = self.session.scalar(stmt)
        if repo is None:
            repo = RepositoryRecord(full_name=full_name, html_url=html_url)
            self.session.add(repo)
            self.session.flush()
        return repo

    def get_audit_by_delivery_id(self, delivery_id: str) -> AuditRecord | None:
        """Retrieve audit by GitHub delivery identifier (for idempotency)."""
        stmt = select(AuditRecord).where(AuditRecord.delivery_id == delivery_id)
        return self.session.scalar(stmt)

    def get_audit(self, audit_id: str) -> AuditRecord | None:
        """Retrieve audit by its primary audit_id."""
        stmt = select(AuditRecord).where(AuditRecord.id == audit_id)
        return self.session.scalar(stmt)

    def get_audit_by_request_id(self, request_id: str) -> AuditRecord | None:
        """Retrieve audit by client idempotency request_id."""
        stmt = select(AuditRecord).where(AuditRecord.request_id == request_id)
        return self.session.scalar(stmt)

    def create_audit(
        self,
        repository_id: str,
        request_id: str,
        head_commit: str,
        base_commit: str | None = None,
        pr_number: int | None = None,
        configuration: str = "D",
        delivery_id: str | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> AuditRecord:
        """Create and persist a new pending audit record."""
        audit = AuditRecord(
            repository_id=repository_id,
            request_id=request_id,
            head_commit=head_commit,
            base_commit=base_commit,
            pr_number=pr_number,
            configuration=configuration,
            delivery_id=delivery_id,
            status="pending",
            provenance=provenance or {},
        )
        self.session.add(audit)
        self.session.flush()
        return audit

    def update_audit_status(
        self,
        audit_id: str,
        status: str,
        error_message: str | None = None,
        duration_seconds: float | None = None,
        provenance: dict[str, Any] | None = None,
    ) -> AuditRecord | None:
        """Update lifecycle status, error message, and completion metadata."""
        audit = self.get_audit(audit_id)
        if not audit:
            return None

        audit.status = status
        if error_message is not None:
            audit.error_message = error_message
        if duration_seconds is not None:
            audit.duration_seconds = duration_seconds
        if provenance is not None:
            updated_prov = dict(audit.provenance)
            updated_prov.update(provenance)
            audit.provenance = updated_prov

        if status in ("completed", "partial", "failed"):
            audit.completed_at = datetime.now(UTC)

        self.session.flush()
        return audit

    def persist_findings(
        self,
        audit_id: str,
        findings: list[PredictedFinding],
    ) -> list[FindingRecord]:
        """Save normalized predicted findings linked to an audit."""
        records: list[FindingRecord] = []
        for f in findings:
            rec = FindingRecord(
                id=f.finding_id,
                audit_id=audit_id,
                detection_layer=str(f.detection_layer),
                tool_name=f.tool_name,
                category_id=f.category_id,
                primary_cwe=f.primary_cwe,
                alternative_cwes=f.alternative_cwes,
                file_path=f.file_path,
                start_line=f.start_line,
                end_line=f.end_line,
                severity=str(f.severity),
                confidence=str(f.confidence),
                title=f.title,
                description=f.description,
                suggestion=f.suggestion,
                provenance=f.provenance,
            )
            self.session.add(rec)
            records.append(rec)
        self.session.flush()
        return records

    def get_findings_for_audit(self, audit_id: str) -> list[FindingRecord]:
        """Retrieve all findings associated with an audit run."""
        stmt = select(FindingRecord).where(FindingRecord.audit_id == audit_id)
        return list(self.session.scalars(stmt).all())

    def record_feedback_result(
        self,
        audit_id: str,
        feedback_status: str,
        comment_id: int | None = None,
        error: str | None = None,
    ) -> AuditRecord | None:
        """Record PR feedback publication outcome in audit provenance."""
        audit = self.get_audit(audit_id)
        if not audit:
            return None

        feedback_info: dict[str, Any] = {
            "status": feedback_status,
            "comment_id": comment_id,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        if error:
            feedback_info["error"] = error

        prov = dict(audit.provenance or {})
        existing_feedback = dict(prov.get("feedback") or {})
        existing_feedback.update(feedback_info)
        prov["feedback"] = existing_feedback
        audit.provenance = prov
        self.session.flush()
        return audit
