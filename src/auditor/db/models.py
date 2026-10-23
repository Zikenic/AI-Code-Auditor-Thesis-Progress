"""Database models for audit persistence."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class for SQLAlchemy models."""
    pass


class RepositoryRecord(Base):
    """Represents a monitored or audited repository."""

    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    html_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    audits: Mapped[list["AuditRecord"]] = relationship("AuditRecord", back_populates="repository", cascade="all, delete-orphan")


class AuditRecord(Base):
    """Represents an execution run of an audit on a repository/commit."""

    __tablename__ = "audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: f"audit-{uuid.uuid4().hex[:12]}")
    request_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    repository_id: Mapped[str] = mapped_column(String(36), ForeignKey("repositories.id"), nullable=False, index=True)
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    head_commit: Mapped[str] = mapped_column(String(40), nullable=False)
    base_commit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    configuration: Mapped[str] = mapped_column(String(10), default="D", nullable=False)

    # Lifecycle status: pending, running, completed, partial, failed
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # GitHub Webhook Delivery ID for idempotency deduplication
    delivery_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)

    # Execution metadata / provenance
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    repository: Mapped["RepositoryRecord"] = relationship("RepositoryRecord", back_populates="audits")
    findings: Mapped[list["FindingRecord"]] = relationship("FindingRecord", back_populates="audit", cascade="all, delete-orphan")


class FindingRecord(Base):
    """Represents a normalized finding emitted by static or LLM engines."""

    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    audit_id: Mapped[str] = mapped_column(String(36), ForeignKey("audits.id"), nullable=False, index=True)

    detection_layer: Mapped[str] = mapped_column(String(32), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, nullable=False)
    primary_cwe: Mapped[str] = mapped_column(String(32), nullable=False)
    alternative_cwes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_line: Mapped[int | None] = mapped_column(Integer, nullable=True)

    severity: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    confidence: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    # Relationships
    audit: Mapped["AuditRecord"] = relationship("AuditRecord", back_populates="findings")
