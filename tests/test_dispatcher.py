"""Unit tests for configuration dispatch, argument-level isolation, and stage error handling."""

from typing import Any

import pytest

from auditor.models.config import AuditConfiguration
from auditor.models.finding import DetectionLayer, PredictedFinding
from auditor.models.request import AuditRequest
from auditor.models.result import AuditStatus
from auditor.orchestration.dispatcher import ConfigurationDispatcher
from auditor.orchestration.interfaces import (
    IDiffProvider,
    ILlmReviewEngine,
    IRepoContextRetriever,
    IStaticAnalysisEngine,
)

# Explicitly distinct sentinel values for proving data isolation
SENTINEL_WORKSPACE = "d:/thesis/workspace/sentinel"
SENTINEL_DIFF = "SENTINEL-DIFF-PAYLOAD-UNIFIED-PATCH-ABC123"
SENTINEL_CHANGED_FILES = ["src/handlers/auth.py", "src/services/session.py"]

SENTINEL_STATIC_FINDINGS = [
    PredictedFinding(
        finding_id="SENTINEL-STATIC-001",
        detection_layer=DetectionLayer.DETERMINISTIC_STATIC,
        tool_name="ruff",
        category_id=2,
        primary_cwe="CWE-20",
        file_path="src/handlers/auth.py",
        start_line=15,
        end_line=15,
        title="Sentinel Static Lint Finding",
        description="Unvalidated user parameter",
    )
]

SENTINEL_LLM_FINDINGS = [
    PredictedFinding(
        finding_id="SENTINEL-LLM-001",
        detection_layer=DetectionLayer.HEURISTIC_LLM,
        tool_name="gemini-1.5-pro",
        category_id=3,
        primary_cwe="CWE-89",
        file_path="src/services/session.py",
        start_line=45,
        end_line=50,
        title="Sentinel LLM Semantic Finding",
        description="Raw SQL query string interpolation",
    )
]

SENTINEL_REPO_CONTEXT = "SENTINEL-REPO-GRAPH-CONTEXT-PAYLOAD-XYZ987"


class SpyDiffProvider(IDiffProvider):
    """Recording spy for diff acquisition."""

    def __init__(self, diff: str = SENTINEL_DIFF, files: list[str] | None = None, fail: bool = False):
        self.diff = diff
        self.files = files or list(SENTINEL_CHANGED_FILES)
        self.fail = fail
        self.calls: list[AuditRequest] = []

    def get_diff(self, request: AuditRequest) -> tuple[str, list[str]]:
        self.calls.append(request)
        if self.fail:
            raise RuntimeError("Git diff provider failed to resolve revisions")
        return self.diff, self.files


class SpyStaticAnalysisEngine(IStaticAnalysisEngine):
    """Recording spy for deterministic static analysis engine."""

    def __init__(self, findings: list[PredictedFinding] | None = None, fail: bool = False):
        self.findings = findings if findings is not None else list(SENTINEL_STATIC_FINDINGS)
        self.fail = fail
        self.calls: list[dict[str, Any]] = []

    def run_static_analysis(
        self,
        workspace_path: str | None,
        changed_files: list[str],
    ) -> list[PredictedFinding]:
        self.calls.append(
            {
                "workspace_path": workspace_path,
                "changed_files": list(changed_files),
            }
        )
        if self.fail:
            raise RuntimeError("Static analysis tool crashed")
        return self.findings


class SpyLlmReviewEngine(ILlmReviewEngine):
    """Recording spy for heuristic LLM review engine."""

    def __init__(self, findings: list[PredictedFinding] | None = None, fail: bool = False):
        self.findings = findings if findings is not None else list(SENTINEL_LLM_FINDINGS)
        self.fail = fail
        self.calls: list[dict[str, Any]] = []

    def run_llm_review(
        self,
        diff_content: str,
        static_findings: list[PredictedFinding] | None = None,
        repo_context: str | None = None,
    ) -> list[PredictedFinding]:
        self.calls.append(
            {
                "diff_content": diff_content,
                "static_findings": static_findings,
                "repo_context": repo_context,
            }
        )
        if self.fail:
            raise RuntimeError("LLM API gateway timeout (HTTP 504)")
        return self.findings


class SpyRepoContextRetriever(IRepoContextRetriever):
    """Recording spy for repository context retriever."""

    def __init__(self, context: str = SENTINEL_REPO_CONTEXT, fail: bool = False):
        self.context = context
        self.fail = fail
        self.calls: list[dict[str, Any]] = []

    def retrieve_context(
        self,
        workspace_path: str | None,
        changed_files: list[str],
        diff_content: str,
    ) -> str:
        self.calls.append(
            {
                "workspace_path": workspace_path,
                "changed_files": list(changed_files),
                "diff_content": diff_content,
            }
        )
        if self.fail:
            raise RuntimeError("Context index database connection lost")
        return self.context


@pytest.fixture
def base_request() -> AuditRequest:
    return AuditRequest(
        request_id="REQ-SENTINEL-001",
        repository_id="owner/repo",
        pr_number=42,
        head_commit="head_sha_123",
        base_commit="base_sha_456",
        workspace_path=SENTINEL_WORKSPACE,
    )


class TestArgumentLevelConfigurationBoundaries:
    """Rigorous argument-level data isolation tests for Configurations A, B, C, and D."""

    def test_configuration_a_argument_level_isolation(self, base_request: AuditRequest):
        """Configuration A: Static analysis executes; LLM and context retriever are never invoked."""
        spy_diff = SpyDiffProvider()
        spy_static = SpyStaticAnalysisEngine()
        spy_llm = SpyLlmReviewEngine()
        spy_context = SpyRepoContextRetriever()

        dispatcher = ConfigurationDispatcher(
            diff_provider=spy_diff,
            static_engine=spy_static,
            llm_engine=spy_llm,
            context_retriever=spy_context,
        )

        base_request.configuration = AuditConfiguration.A
        result = dispatcher.dispatch(base_request)

        # 1. Output assertions
        assert result.status == AuditStatus.SUCCESS
        assert result.configuration == AuditConfiguration.A
        assert result.findings == SENTINEL_STATIC_FINDINGS

        # 2. Argument-level spy checks for Static Engine
        assert len(spy_static.calls) == 1
        assert spy_static.calls[0]["workspace_path"] == SENTINEL_WORKSPACE
        assert spy_static.calls[0]["changed_files"] == SENTINEL_CHANGED_FILES

        # 3. Isolation assertions: LLM and Context Retriever must NOT be invoked
        assert len(spy_llm.calls) == 0, "LLM engine must never be invoked in Configuration A"
        assert len(spy_context.calls) == 0, "Context retriever must never be invoked in Configuration A"

    def test_configuration_b_argument_level_isolation(self, base_request: AuditRequest):
        """Configuration B: LLM executes with diff only; static engine and context retriever never invoked.

        Static findings and repo context received by LLM MUST be None.
        """
        spy_diff = SpyDiffProvider()
        spy_static = SpyStaticAnalysisEngine()
        spy_llm = SpyLlmReviewEngine()
        spy_context = SpyRepoContextRetriever()

        dispatcher = ConfigurationDispatcher(
            diff_provider=spy_diff,
            static_engine=spy_static,
            llm_engine=spy_llm,
            context_retriever=spy_context,
        )

        base_request.configuration = AuditConfiguration.B
        result = dispatcher.dispatch(base_request)

        # 1. Output assertions
        assert result.status == AuditStatus.SUCCESS
        assert result.configuration == AuditConfiguration.B
        assert result.findings == SENTINEL_LLM_FINDINGS

        # 2. Isolation assertions: Static engine and Context Retriever must NOT be invoked
        assert len(spy_static.calls) == 0, "Static analysis must never be invoked in Configuration B"
        assert len(spy_context.calls) == 0, "Context retriever must never be invoked in Configuration B"

        # 3. Argument-level spy checks for LLM Engine
        assert len(spy_llm.calls) == 1
        call_args = spy_llm.calls[0]
        assert call_args["diff_content"] == SENTINEL_DIFF
        assert call_args["static_findings"] is None, "Configuration B must NOT pass static findings to LLM"
        assert call_args["repo_context"] is None, "Configuration B must NOT pass repository context to LLM"

    def test_configuration_c_argument_level_isolation(self, base_request: AuditRequest):
        """Configuration C: Static analysis and LLM execute; repository context retriever never invoked.

        LLM receives static findings, but repo context MUST be None.
        """
        spy_diff = SpyDiffProvider()
        spy_static = SpyStaticAnalysisEngine()
        spy_llm = SpyLlmReviewEngine()
        spy_context = SpyRepoContextRetriever()

        dispatcher = ConfigurationDispatcher(
            diff_provider=spy_diff,
            static_engine=spy_static,
            llm_engine=spy_llm,
            context_retriever=spy_context,
        )

        base_request.configuration = AuditConfiguration.C
        result = dispatcher.dispatch(base_request)

        # 1. Output assertions
        assert result.status == AuditStatus.SUCCESS
        assert result.configuration == AuditConfiguration.C
        assert len(result.findings) == 2  # 1 static finding + 1 LLM finding

        # 2. Argument-level spy checks for Static Engine
        assert len(spy_static.calls) == 1
        assert spy_static.calls[0]["workspace_path"] == SENTINEL_WORKSPACE
        assert spy_static.calls[0]["changed_files"] == SENTINEL_CHANGED_FILES

        # 3. Isolation assertions: Context Retriever must NOT be invoked
        assert len(spy_context.calls) == 0, "Context retriever must never be invoked in Configuration C"

        # 4. Argument-level spy checks for LLM Engine
        assert len(spy_llm.calls) == 1
        call_args = spy_llm.calls[0]
        assert call_args["diff_content"] == SENTINEL_DIFF
        assert call_args["static_findings"] == SENTINEL_STATIC_FINDINGS, "Static findings must reach LLM in Config C"
        assert call_args["repo_context"] is None, "Repository context must NEVER leak into Configuration C"

    def test_configuration_d_argument_level_isolation(self, base_request: AuditRequest):
        """Configuration D: Full hybrid pipeline with repository context retrieval.

        LLM receives diff, static findings, and repository context payload.
        """
        spy_diff = SpyDiffProvider()
        spy_static = SpyStaticAnalysisEngine()
        spy_llm = SpyLlmReviewEngine()
        spy_context = SpyRepoContextRetriever()

        dispatcher = ConfigurationDispatcher(
            diff_provider=spy_diff,
            static_engine=spy_static,
            llm_engine=spy_llm,
            context_retriever=spy_context,
        )

        base_request.configuration = AuditConfiguration.D
        result = dispatcher.dispatch(base_request)

        # 1. Output assertions
        assert result.status == AuditStatus.SUCCESS
        assert result.configuration == AuditConfiguration.D
        assert len(result.findings) == 2

        # 2. Argument-level spy checks for Static Engine
        assert len(spy_static.calls) == 1
        assert spy_static.calls[0]["workspace_path"] == SENTINEL_WORKSPACE
        assert spy_static.calls[0]["changed_files"] == SENTINEL_CHANGED_FILES

        # 3. Argument-level spy checks for Context Retriever
        assert len(spy_context.calls) == 1
        assert spy_context.calls[0]["workspace_path"] == SENTINEL_WORKSPACE
        assert spy_context.calls[0]["changed_files"] == SENTINEL_CHANGED_FILES
        assert spy_context.calls[0]["diff_content"] == SENTINEL_DIFF

        # 4. Argument-level spy checks for LLM Engine
        assert len(spy_llm.calls) == 1
        call_args = spy_llm.calls[0]
        assert call_args["diff_content"] == SENTINEL_DIFF
        assert call_args["static_findings"] == SENTINEL_STATIC_FINDINGS
        assert call_args["repo_context"] == SENTINEL_REPO_CONTEXT, "Repo context must reach LLM in Config D"


class TestDispatcherErrorHandlingAndDegradation:
    """Verifies observable status and failure degradation across all stages."""

    def test_diff_failure_produces_failed_status(self, base_request: AuditRequest):
        dispatcher = ConfigurationDispatcher(
            diff_provider=SpyDiffProvider(fail=True),
        )
        base_request.configuration = AuditConfiguration.A
        result = dispatcher.dispatch(base_request)

        assert result.status == AuditStatus.FAILED
        assert "Diff acquisition failed" in result.error_message
        assert len(result.findings) == 0

    def test_static_failure_in_config_a_produces_failed_status(self, base_request: AuditRequest):
        dispatcher = ConfigurationDispatcher(
            diff_provider=SpyDiffProvider(),
            static_engine=SpyStaticAnalysisEngine(fail=True),
        )
        base_request.configuration = AuditConfiguration.A
        result = dispatcher.dispatch(base_request)

        assert result.status == AuditStatus.FAILED
        assert "Static analysis failed in Config A" in result.error_message
        assert len(result.findings) == 0

    def test_llm_failure_in_config_b_produces_failed_status(self, base_request: AuditRequest):
        dispatcher = ConfigurationDispatcher(
            diff_provider=SpyDiffProvider(),
            llm_engine=SpyLlmReviewEngine(fail=True),
        )
        base_request.configuration = AuditConfiguration.B
        result = dispatcher.dispatch(base_request)

        assert result.status == AuditStatus.FAILED
        assert "LLM review failed in Config B" in result.error_message

    def test_static_failure_in_config_c_produces_failed_status(self, base_request: AuditRequest):
        dispatcher = ConfigurationDispatcher(
            diff_provider=SpyDiffProvider(),
            static_engine=SpyStaticAnalysisEngine(fail=True),
            llm_engine=SpyLlmReviewEngine(),
        )
        base_request.configuration = AuditConfiguration.C
        result = dispatcher.dispatch(base_request)

        assert result.status == AuditStatus.FAILED
        assert "Static analysis failed in Config C" in result.error_message

    def test_llm_failure_in_config_c_produces_partial_status_preserving_static(self, base_request: AuditRequest):
        dispatcher = ConfigurationDispatcher(
            diff_provider=SpyDiffProvider(),
            static_engine=SpyStaticAnalysisEngine(),
            llm_engine=SpyLlmReviewEngine(fail=True),
        )
        base_request.configuration = AuditConfiguration.C
        result = dispatcher.dispatch(base_request)

        assert result.status == AuditStatus.PARTIAL
        assert "returning static findings only" in result.error_message
        assert len(result.findings) == 1
        assert result.findings[0].detection_layer == DetectionLayer.DETERMINISTIC_STATIC

    def test_static_failure_in_config_d_produces_failed_status(self, base_request: AuditRequest):
        dispatcher = ConfigurationDispatcher(
            diff_provider=SpyDiffProvider(),
            static_engine=SpyStaticAnalysisEngine(fail=True),
            context_retriever=SpyRepoContextRetriever(),
            llm_engine=SpyLlmReviewEngine(),
        )
        base_request.configuration = AuditConfiguration.D
        result = dispatcher.dispatch(base_request)

        assert result.status == AuditStatus.FAILED
        assert "Static analysis failed in Config D" in result.error_message

    def test_context_retrieval_failure_in_config_d_produces_failed_status(self, base_request: AuditRequest):
        dispatcher = ConfigurationDispatcher(
            diff_provider=SpyDiffProvider(),
            static_engine=SpyStaticAnalysisEngine(),
            context_retriever=SpyRepoContextRetriever(fail=True),
            llm_engine=SpyLlmReviewEngine(),
        )
        base_request.configuration = AuditConfiguration.D
        result = dispatcher.dispatch(base_request)

        assert result.status == AuditStatus.FAILED
        assert "Repository context retrieval failed in Config D" in result.error_message

    def test_llm_failure_in_config_d_produces_partial_status_preserving_static(self, base_request: AuditRequest):
        dispatcher = ConfigurationDispatcher(
            diff_provider=SpyDiffProvider(),
            static_engine=SpyStaticAnalysisEngine(),
            context_retriever=SpyRepoContextRetriever(),
            llm_engine=SpyLlmReviewEngine(fail=True),
        )
        base_request.configuration = AuditConfiguration.D
        result = dispatcher.dispatch(base_request)

        assert result.status == AuditStatus.PARTIAL
        assert "returning static findings only" in result.error_message
        assert len(result.findings) == 1
        assert result.findings[0].detection_layer == DetectionLayer.DETERMINISTIC_STATIC
