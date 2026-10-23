"""Adapter connecting ConfigBAuditEngine to ILlmReviewEngine interface for ConfigurationDispatcher."""

from __future__ import annotations

from auditor.llm.engine import ConfigBAuditEngine
from auditor.llm.hybrid_engine import ConfigCHybridReviewEngine
from auditor.models.finding import PredictedFinding
from auditor.models.result import AuditStatus
from auditor.orchestration.interfaces import ILlmReviewEngine


class ConfigBLlmReviewEngineAdapter(ILlmReviewEngine):
    """Adapts ConfigBAuditEngine to ConfigurationDispatcher's ILlmReviewEngine interface."""

    def __init__(self, engine: ConfigBAuditEngine, target_file_path: str = "target.py"):
        self.engine = engine
        self.target_file_path = target_file_path

    def run_llm_review(
        self,
        diff_content: str,
        static_findings: list[PredictedFinding] | None = None,
        repo_context: str | None = None,
        **kwargs,
    ) -> list[PredictedFinding]:
        """Execute LLM review through ConfigBAuditEngine.

        Under Configuration B invariants, static_findings and repo_context are ignored / None.
        diff_content provides the source text.
        """
        status, findings, _ = self.engine.audit_source(
            raw_source=diff_content,
            file_path=self.target_file_path,
        )
        if status != AuditStatus.SUCCESS:
            raise RuntimeError(f"ConfigBAuditEngine execution failed (status: {status.value})")
        return findings


class ConfigCLlmReviewEngineAdapter(ConfigCHybridReviewEngine):
    """Adapter for Configuration C hybrid review engine adhering to ILlmReviewEngine."""

    pass
