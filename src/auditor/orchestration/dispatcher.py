"""Configuration dispatcher enforcing strict experimental boundaries across Configurations A–D."""

import uuid

from auditor.models.config import AuditConfiguration
from auditor.models.finding import PredictedFinding
from auditor.models.request import AuditRequest
from auditor.models.result import AuditRunResult, AuditStatus
from auditor.orchestration.interfaces import (
    IDiffProvider,
    ILlmReviewEngine,
    IRepoContextRetriever,
    IStaticAnalysisEngine,
    UnimplementedDiffProvider,
    UnimplementedLlmReviewEngine,
    UnimplementedRepoContextRetriever,
)


class ConfigurationDispatcher:
    """Core auditor orchestrator enforcing strict isolation across Configurations A, B, C, and D.

    - CONFIG_A: Static analysis only; zero LLM invocation; zero repo context.
    - CONFIG_B: LLM review with PR diff only; zero static analysis; zero repo context.
    - CONFIG_C: Static analysis + LLM review with static summary; zero repo context.
    - CONFIG_D: Static analysis + Repo context retrieval + LLM review.
    """

    def __init__(
        self,
        diff_provider: IDiffProvider | None = None,
        static_engine: IStaticAnalysisEngine | None = None,
        llm_engine: ILlmReviewEngine | None = None,
        context_retriever: IRepoContextRetriever | None = None,
    ):
        if static_engine is None:
            from auditor.static_analysis.engine import StaticAnalysisEngine

            static_engine = StaticAnalysisEngine()

        self.diff_provider = diff_provider or UnimplementedDiffProvider()
        self.static_engine = static_engine
        self.llm_engine = llm_engine or UnimplementedLlmReviewEngine()
        self.context_retriever = context_retriever or UnimplementedRepoContextRetriever()

    def dispatch(self, request: AuditRequest) -> AuditRunResult:
        """Execute audit pipeline according to the request's configured AuditConfiguration."""
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        config = request.configuration

        # 1. Acquire diff and changed files
        try:
            diff_content, changed_files = self.diff_provider.get_diff(request)
        except Exception as e:
            return AuditRunResult(
                run_id=run_id,
                request_id=request.request_id,
                configuration=config,
                status=AuditStatus.FAILED,
                findings=[],
                error_message=f"Diff acquisition failed: {str(e)}",
            )

        static_findings: list[PredictedFinding] = []
        llm_findings: list[PredictedFinding] = []

        # 2. Execute Configuration A (Static Baseline Only)
        if config == AuditConfiguration.A:
            try:
                static_findings = self.static_engine.run_static_analysis(
                    workspace_path=request.workspace_path,
                    changed_files=changed_files,
                )
                return AuditRunResult(
                    run_id=run_id,
                    request_id=request.request_id,
                    configuration=config,
                    status=AuditStatus.SUCCESS,
                    findings=static_findings,
                    provenance={"stage": "static_only", "files_analyzed": len(changed_files)},
                )
            except Exception as e:
                return AuditRunResult(
                    run_id=run_id,
                    request_id=request.request_id,
                    configuration=config,
                    status=AuditStatus.FAILED,
                    findings=[],
                    error_message=f"Static analysis failed in Config A: {str(e)}",
                )

        # 3. Execute Configuration B (Isolated LLM Review Only)
        elif config == AuditConfiguration.B:
            try:
                llm_findings = self.llm_engine.run_llm_review(
                    diff_content=diff_content,
                    static_findings=None,
                    repo_context=None,
                )
                return AuditRunResult(
                    run_id=run_id,
                    request_id=request.request_id,
                    configuration=config,
                    status=AuditStatus.SUCCESS,
                    findings=llm_findings,
                    provenance={"stage": "llm_only_isolated"},
                )
            except Exception as e:
                return AuditRunResult(
                    run_id=run_id,
                    request_id=request.request_id,
                    configuration=config,
                    status=AuditStatus.FAILED,
                    findings=[],
                    error_message=f"LLM review failed in Config B: {str(e)}",
                )

        # 4. Execute Configuration C (Hybrid, No Repo Context)
        elif config == AuditConfiguration.C:
            try:
                static_findings = self.static_engine.run_static_analysis(
                    workspace_path=request.workspace_path,
                    changed_files=changed_files,
                )
            except Exception as e:
                return AuditRunResult(
                    run_id=run_id,
                    request_id=request.request_id,
                    configuration=config,
                    status=AuditStatus.FAILED,
                    findings=[],
                    error_message=f"Static analysis failed in Config C: {str(e)}",
                )

            try:
                try:
                    llm_findings = self.llm_engine.run_llm_review(
                        diff_content=diff_content,
                        static_findings=static_findings,
                        repo_context=None,
                        workspace_path=request.workspace_path,
                        changed_files=changed_files,
                    )
                except TypeError:
                    llm_findings = self.llm_engine.run_llm_review(
                        diff_content=diff_content,
                        static_findings=static_findings,
                        repo_context=None,
                    )
                all_findings = self._combine_findings(static_findings, llm_findings)
                return AuditRunResult(
                    run_id=run_id,
                    request_id=request.request_id,
                    configuration=config,
                    status=AuditStatus.SUCCESS,
                    findings=all_findings,
                    provenance={"stage": "hybrid_no_repo_context"},
                )
            except Exception as e:
                # Graceful degradation: return partial static findings with failure warning
                return AuditRunResult(
                    run_id=run_id,
                    request_id=request.request_id,
                    configuration=config,
                    status=AuditStatus.PARTIAL,
                    findings=static_findings,
                    error_message=f"LLM stage failed in Config C; returning static findings only: {str(e)}",
                    provenance={"stage": "hybrid_no_repo_context", "degraded": True},
                )

        # 5. Execute Configuration D (Full Hybrid with Repo Context)
        elif config == AuditConfiguration.D:
            try:
                static_findings = self.static_engine.run_static_analysis(
                    workspace_path=request.workspace_path,
                    changed_files=changed_files,
                )
            except Exception as e:
                return AuditRunResult(
                    run_id=run_id,
                    request_id=request.request_id,
                    configuration=config,
                    status=AuditStatus.FAILED,
                    findings=[],
                    error_message=f"Static analysis failed in Config D: {str(e)}",
                )

            repo_context = ""
            try:
                repo_context = self.context_retriever.retrieve_context(
                    workspace_path=request.workspace_path,
                    changed_files=changed_files,
                    diff_content=diff_content,
                )
            except Exception as e:
                return AuditRunResult(
                    run_id=run_id,
                    request_id=request.request_id,
                    configuration=config,
                    status=AuditStatus.FAILED,
                    findings=[],
                    error_message=f"Repository context retrieval failed in Config D: {str(e)}",
                )

            try:
                llm_findings = self.llm_engine.run_llm_review(
                    diff_content=diff_content,
                    static_findings=static_findings,
                    repo_context=repo_context,
                )
                all_findings = self._combine_findings(static_findings, llm_findings)
                return AuditRunResult(
                    run_id=run_id,
                    request_id=request.request_id,
                    configuration=config,
                    status=AuditStatus.SUCCESS,
                    findings=all_findings,
                    provenance={"stage": "hybrid_with_repo_context"},
                )
            except Exception as e:
                return AuditRunResult(
                    run_id=run_id,
                    request_id=request.request_id,
                    configuration=config,
                    status=AuditStatus.PARTIAL,
                    findings=static_findings,
                    error_message=f"LLM stage failed in Config D; returning static findings only: {str(e)}",
                    provenance={"stage": "hybrid_with_repo_context", "degraded": True},
                )

        raise ValueError(f"Unknown audit configuration: {config}")

    def _combine_findings(
        self,
        static_findings: list[PredictedFinding],
        llm_findings: list[PredictedFinding],
    ) -> list[PredictedFinding]:
        """Aggregate static and LLM findings, merging triage metadata into static findings."""
        from auditor.models.finding import DetectionLayer

        combined: list[PredictedFinding] = []
        static_by_id = {f.finding_id: f for f in static_findings}
        seen_keys = set()

        # 1. Merge triage annotations into static findings if present in llm_findings
        for f in llm_findings:
            if f.finding_id in static_by_id:
                target = static_by_id[f.finding_id]
                target.provenance.update(f.provenance)
                if f.suggestion and not target.suggestion:
                    target.suggestion = f.suggestion
            elif f.detection_layer == DetectionLayer.DETERMINISTIC_STATIC:
                for target in static_findings:
                    if (
                        target.file_path == f.file_path
                        and target.start_line == f.start_line
                        and target.primary_cwe == f.primary_cwe
                    ):
                        target.provenance.update(f.provenance)
                        break

        # 2. Add static findings (with merged triage metadata)
        for f in static_findings:
            key = (f.file_path, f.start_line, f.primary_cwe, f.detection_layer)
            if key not in seen_keys:
                seen_keys.add(key)
                combined.append(f)

        # 3. Add additional LLM findings (layer HEURISTIC_LLM or new IDs)
        for f in llm_findings:
            if f.finding_id not in static_by_id:
                key = (f.file_path, f.start_line, f.primary_cwe, f.detection_layer)
                if key not in seen_keys:
                    seen_keys.add(key)
                    combined.append(f)

        return combined
