"""Unit and integration tests for database persistence models and repository."""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from auditor.db.models import Base
from auditor.db.repository import AuditRepository
from auditor.models.finding import ConfidenceLevel, DetectionLayer, PredictedFinding, SeverityLevel


@pytest.fixture
def test_db_session():
    """Create an isolated in-memory SQLite database and provide a test session."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_repository_get_or_create(test_db_session):
    repo = AuditRepository(test_db_session)
    r1 = repo.get_or_create_repository(full_name="tiangolo/fastapi", html_url="https://github.com/tiangolo/fastapi")
    test_db_session.commit()

    assert r1.id is not None
    assert r1.full_name == "tiangolo/fastapi"
    assert r1.html_url == "https://github.com/tiangolo/fastapi"

    # Query again should return existing record
    r2 = repo.get_or_create_repository(full_name="tiangolo/fastapi")
    assert r2.id == r1.id


def test_audit_lifecycle_and_relationships(test_db_session):
    repo = AuditRepository(test_db_session)
    r = repo.get_or_create_repository(full_name="pallets/flask")
    test_db_session.commit()

    req_id = f"req-{uuid.uuid4().hex[:8]}"
    audit = repo.create_audit(
        repository_id=r.id,
        request_id=req_id,
        head_commit="abcdef1234567890abcdef1234567890abcdef12",
        base_commit="1234567890abcdef1234567890abcdef12345678",
        pr_number=42,
        configuration="D",
        delivery_id="deliv-101",
        provenance={"trigger": "test"},
    )
    test_db_session.commit()

    assert audit.id.startswith("audit-")
    assert audit.status == "pending"
    assert audit.pr_number == 42
    assert audit.repository.full_name == "pallets/flask"

    # Query by delivery_id
    by_deliv = repo.get_audit_by_delivery_id("deliv-101")
    assert by_deliv is not None
    assert by_deliv.id == audit.id

    # Update status to running
    repo.update_audit_status(audit.id, status="running")
    test_db_session.commit()
    assert repo.get_audit(audit.id).status == "running"

    # Update status to completed
    repo.update_audit_status(audit.id, status="completed", duration_seconds=1.25)
    test_db_session.commit()
    completed_audit = repo.get_audit(audit.id)
    assert completed_audit.status == "completed"
    assert completed_audit.duration_seconds == 1.25
    assert completed_audit.completed_at is not None


def test_findings_persistence_and_retrieval(test_db_session):
    repo = AuditRepository(test_db_session)
    r = repo.get_or_create_repository(full_name="encode/starlette")
    audit = repo.create_audit(
        repository_id=r.id,
        request_id="req-f-1",
        head_commit="a" * 40,
    )
    test_db_session.commit()

    finding1 = PredictedFinding(
        finding_id="f-uuid-1",
        detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
        tool_name="ruff",
        category_id=1,
        primary_cwe="CWE-670",
        alternative_cwes=["CWE-20"],
        file_path="starlette/routing.py",
        start_line=10,
        end_line=12,
        severity=SeverityLevel.HIGH,
        confidence=ConfidenceLevel.HIGH,
        title="Logic boundary flaw",
        description="Detailed description of boundary condition flaw.",
        suggestion="Fix boundary check.",
        provenance={"rule_code": "B001"},
    )

    records = repo.persist_findings(audit.id, [finding1])
    test_db_session.commit()

    assert len(records) == 1
    assert records[0].id == "f-uuid-1"

    # Query back
    stored = repo.get_findings_for_audit(audit.id)
    assert len(stored) == 1
    assert stored[0].primary_cwe == "CWE-670"
    assert stored[0].alternative_cwes == ["CWE-20"]
    assert stored[0].file_path == "starlette/routing.py"
    assert stored[0].start_line == 10
    assert stored[0].severity == "high"


def test_transaction_rollback_on_error(test_db_session):
    repo = AuditRepository(test_db_session)
    r = repo.get_or_create_repository(full_name="test/repo")
    test_db_session.commit()

    # Attempt to insert two audits with identical unique request_id
    repo.create_audit(repository_id=r.id, request_id="unique-req", head_commit="a" * 40)
    test_db_session.commit()

    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        repo.create_audit(repository_id=r.id, request_id="unique-req", head_commit="b" * 40)
        test_db_session.commit()

    test_db_session.rollback()
    # Confirm DB remains in consistent state
    audit = repo.get_audit_by_request_id("unique-req")
    assert audit is not None
    assert audit.head_commit == "a" * 40
