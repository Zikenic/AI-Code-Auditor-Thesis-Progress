"""Abstract component interfaces for the AI Code Auditor pipeline."""

from abc import ABC, abstractmethod

from auditor.models.finding import PredictedFinding
from auditor.models.request import AuditRequest


class IDiffProvider(ABC):
    """Acquires code diff and modified file list for an audit request."""

    @abstractmethod
    def get_diff(self, request: AuditRequest) -> tuple[str, list[str]]:
        """Return (unified_diff_content, list_of_modified_file_paths)."""
        pass


class IStaticAnalysisEngine(ABC):
    """Executes deterministic static analysis tools (Ruff and Semgrep CE)."""

    @abstractmethod
    def run_static_analysis(
        self,
        workspace_path: str | None,
        changed_files: list[str],
    ) -> list[PredictedFinding]:
        """Run deterministic static checks and emit normalized findings."""
        pass


class IRepoContextRetriever(ABC):
    """Retrieves repository-wide context (AST call graphs and vector embeddings)."""

    @abstractmethod
    def retrieve_context(
        self,
        workspace_path: str | None,
        changed_files: list[str],
        diff_content: str,
    ) -> str:
        """Extract and format repository context without context window overflow."""
        pass


class ILlmReviewEngine(ABC):
    """Invokes LLM API client for semantic intent and vulnerability review."""

    @abstractmethod
    def run_llm_review(
        self,
        diff_content: str,
        static_findings: list[PredictedFinding] | None = None,
        repo_context: str | None = None,
    ) -> list[PredictedFinding]:
        """Execute heuristic LLM review and return parsed, validated findings."""
        pass


# Explicitly marked unimplemented adapters for future implementation slices
class UnimplementedDiffProvider(IDiffProvider):
    def get_diff(self, request: AuditRequest) -> tuple[str, list[str]]:
        raise NotImplementedError("Production DiffProvider is not yet implemented in this slice.")


class UnimplementedStaticAnalysisEngine(IStaticAnalysisEngine):
    def run_static_analysis(
        self,
        workspace_path: str | None,
        changed_files: list[str],
    ) -> list[PredictedFinding]:
        raise NotImplementedError(
            "Production StaticAnalysisEngine (Ruff/Semgrep CLI wrapper) is not yet implemented in this slice."
        )


class UnimplementedRepoContextRetriever(IRepoContextRetriever):
    def retrieve_context(
        self,
        workspace_path: str | None,
        changed_files: list[str],
        diff_content: str,
    ) -> str:
        raise NotImplementedError(
            "Production RepoContextRetriever (AST/pgvector) is not yet implemented in this slice."
        )


class UnimplementedLlmReviewEngine(ILlmReviewEngine):
    def run_llm_review(
        self,
        diff_content: str,
        static_findings: list[PredictedFinding] | None = None,
        repo_context: str | None = None,
    ) -> list[PredictedFinding]:
        raise NotImplementedError("Production LlmReviewEngine (API client) is not yet implemented in this slice.")
