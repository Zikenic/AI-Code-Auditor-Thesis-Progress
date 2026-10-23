"""Reproducible Evaluation Runner for Configurations A, B, C, and D.

Orchestrates:
- Executing Config A (Static Analysis), Config B (LLM-only), Config C (Hybrid), Config D (Contextual Hybrid).
- Isolated workspace materialization per case to avoid cross-contamination.
- Dual execution modes:
  - 'offline': deterministic execution with mock LLM client or historical frozen fixtures.
  - 'live': explicitly enabled execution through authorized local gateway client.
- Strict isolation: zero leaking of repo_context into Config A/B/C.
- Collection of per-case findings, execution status, latency, and telemetry.
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from auditor.dataset.source_resolver import extract_target_file_content, resolve_case_repo_path
from auditor.evaluation.manifest import BenchmarkManifest, ManifestCase
from auditor.evaluation.provenance import ResultProvenance
from auditor.llm.anthropic_client import AnthropicApiClient
from auditor.llm.chunker import SourceChunker
from auditor.llm.config import DEFAULT_CONFIG_B_PARAMS, DEFAULT_CONFIG_C_PARAMS, DEFAULT_CONFIG_D_PARAMS
from auditor.llm.context_retriever import RepositoryContextRetriever, RepositoryIndex
from auditor.llm.credentials import load_gateway_credentials
from auditor.llm.deduplication import deduplicate_findings
from auditor.llm.engine import ConfigBAuditEngine, ILlmApiClient
from auditor.llm.hybrid_engine import ConfigCHybridReviewEngine
from auditor.llm.parser import ConfigBResponseParser
from auditor.llm.prompt_builder import build_config_d_user_prompt, get_system_prompt
from auditor.llm.static_formatter import format_static_findings_section
from auditor.models.finding import PredictedFinding
from auditor.models.result import AuditStatus
from auditor.static_analysis.engine import StaticAnalysisEngine

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
FROZEN_RESULTS_DIR = REPO_ROOT / "data" / "results"


class MockEvaluationLlmClient(ILlmApiClient):
    """Deterministic offline mock LLM client for evaluation dry-runs."""

    def __init__(self, response_map: dict[str, str] | None = None):
        self.response_map = response_map or {}
        self.call_count = 0

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        model_id: str,
        thinking_type: str = "adaptive",
        thinking_effort: str = "medium",
    ) -> tuple[str, int, int]:
        self.call_count += 1
        # Default empty JSON payload
        default_payload = json.dumps({"findings": [], "triage_decisions": [], "additional_findings": []})
        for key, resp in self.response_map.items():
            if key in user_prompt:
                return resp, 300, 100
        return default_payload, 250, 80


@dataclass
class ConfigurationRunOutput:
    """Output results of executing one configuration across benchmark cases."""

    configuration: str
    run_id: str
    mode: str
    predictions_by_case: dict[str, list[PredictedFinding]]
    statuses_by_case: dict[str, str]
    durations_by_case: dict[str, float]
    provenance_by_case: dict[str, dict[str, Any]] | None = None
    cost_usd: float | None = None
    metadata: dict[str, Any] | None = None


class EvaluationRunner:
    """Reproducible evaluation runner executing A/B/C/D pipelines."""

    def __init__(
        self,
        manifest: BenchmarkManifest,
        mode: str = "offline",
        api_client: ILlmApiClient | None = None,
        use_frozen_fixture_fallback: bool = True,
    ):
        self.manifest = manifest
        self.mode = mode.lower()
        self.api_client = api_client
        self.use_frozen_fixture_fallback = use_frozen_fixture_fallback
        self.static_engine = StaticAnalysisEngine()

        if self.mode == "live" and self.api_client is None:
            creds = load_gateway_credentials()
            self.api_client = AnthropicApiClient(credentials=creds, timeout=120.0, max_retries=1)

    def run_case_config_a(
        self,
        case: ManifestCase,
        workspace_dir: Path,
    ) -> tuple[AuditStatus, list[PredictedFinding], float]:
        """Execute Configuration A (Static analysis only) on a single case in an isolated workspace."""
        start_time = time.monotonic()
        try:
            # Materialize target file in isolated workspace
            target_file_path = workspace_dir / case.target_file
            target_file_path.parent.mkdir(parents=True, exist_ok=True)

            code_content = self._resolve_case_code(case)
            target_file_path.write_text(code_content, encoding="utf-8", errors="replace")

            findings = self.static_engine.run_static_analysis(
                workspace_path=str(workspace_dir),
                changed_files=[case.target_file],
            )
            duration = time.monotonic() - start_time
            return AuditStatus.SUCCESS, findings, duration
        except Exception as e:
            duration = time.monotonic() - start_time
            logger.warning("Config A failed for case %s: %s", case.case_id, e)
            return AuditStatus.FAILED, [], duration

    def run_case_config_b(
        self,
        case: ManifestCase,
        workspace_dir: Path,
    ) -> tuple[AuditStatus, list[PredictedFinding], float, dict[str, Any]]:
        """Execute Configuration B (LLM-only code review) on a single case."""
        start_time = time.monotonic()
        try:
            code_content = self._resolve_case_code(case)
            client = self.api_client if self.mode == "live" else MockEvaluationLlmClient()

            engine = ConfigBAuditEngine(api_client=client, config=DEFAULT_CONFIG_B_PARAMS)
            status, findings, meta = engine.audit_source(
                raw_source=code_content,
                file_path=case.target_file,
                case_id=case.case_id,
                config_name="B",
            )
            duration = time.monotonic() - start_time
            return status, findings, duration, meta
        except Exception as e:
            duration = time.monotonic() - start_time
            logger.warning("Config B failed for case %s: %s", case.case_id, e)
            return AuditStatus.FAILED, [], duration, {"error": str(e)}

    def run_case_config_c(
        self,
        case: ManifestCase,
        workspace_dir: Path,
        static_findings: list[PredictedFinding],
    ) -> tuple[AuditStatus, list[PredictedFinding], float, dict[str, Any]]:
        """Execute Configuration C (Hybrid review: static + LLM triage) on a single case."""
        start_time = time.monotonic()
        try:
            code_content = self._resolve_case_code(case)
            client = self.api_client if self.mode == "live" else MockEvaluationLlmClient()

            hybrid_engine = ConfigCHybridReviewEngine(api_client=client, config=DEFAULT_CONFIG_C_PARAMS)
            findings = hybrid_engine.run_llm_review(
                diff_content=code_content,
                static_findings=static_findings,
                repo_context=None,  # Invariant: zero repo context in Config C
                workspace_path=str(workspace_dir),
                changed_files=[case.target_file],
            )
            duration = time.monotonic() - start_time
            return AuditStatus.SUCCESS, findings, duration, hybrid_engine.last_review_telemetry or {}
        except Exception as e:
            duration = time.monotonic() - start_time
            logger.warning("Config C failed for case %s; returning static findings only: %s", case.case_id, e)
            # Graceful degradation preserves static findings with PARTIAL status
            return AuditStatus.PARTIAL, list(static_findings), duration, {"error": str(e)}

    def run_case_config_d(
        self,
        case: ManifestCase,
        workspace_dir: Path,
        static_findings: list[PredictedFinding],
    ) -> tuple[AuditStatus, list[PredictedFinding], float, dict[str, Any]]:
        """Execute Configuration D (Full Hybrid: Static + Context + LLM Review) on a single case."""
        start_time = time.monotonic()
        try:
            code_content = self._resolve_case_code(case)
            client = self.api_client if self.mode == "live" else MockEvaluationLlmClient()

            # 1. Index repository or fixture directory
            if case.fixture_path:
                idx_dir = REPO_ROOT / Path(case.fixture_path).parent
                repo_index = RepositoryIndex(repo_dir=idx_dir, commit_hash=case.commit_hash or "clean")
            else:
                try:
                    bcase = case.to_benchmark_case()
                    repo_path = resolve_case_repo_path(bcase)
                    repo_index = RepositoryIndex(repo_dir=repo_path, commit_hash=case.commit_hash)
                except Exception:
                    repo_index = RepositoryIndex(repo_dir=workspace_dir, commit_hash=case.commit_hash or "clean")

            retriever = RepositoryContextRetriever(repo_index)

            # 2. Chunk source code
            chunker = SourceChunker(token_budget=DEFAULT_CONFIG_D_PARAMS.source_token_budget)
            chunks = chunker.chunk_source(code_content, case.target_file)
            if not chunks:
                return AuditStatus.SUCCESS, [], time.monotonic() - start_time, {}

            system_prompt = get_system_prompt(config="D")
            parser = ConfigBResponseParser(model_name=DEFAULT_CONFIG_D_PARAMS.model_id)

            if self.mode != "live":
                # Deterministic mock offline mode
                return AuditStatus.SUCCESS, [], time.monotonic() - start_time, {"chunks": len(chunks)}

            case_findings: list[PredictedFinding] = []
            total_p_tokens = 0
            total_c_tokens = 0
            raw_responses = []

            from auditor.llm.cost_tracker import CostTracker

            cost_tracker = CostTracker(
                cost_per_input_million=getattr(DEFAULT_CONFIG_D_PARAMS, "cost_per_input_million", 3.0),
                cost_per_output_million=getattr(DEFAULT_CONFIG_D_PARAMS, "cost_per_output_million", 15.0),
            )

            for chunk_idx, chunk in enumerate(chunks, 1):
                static_section, _, _ = format_static_findings_section(
                    findings=[f.model_dump() for f in static_findings],
                    chunk=chunk,
                    token_budget=DEFAULT_CONFIG_D_PARAMS.static_token_budget,
                    token_counter=chunker.count_tokens,
                )

                context_section, _, _ = retriever.retrieve_context(
                    target_file=case.target_file,
                    chunk_start=chunk.start_line,
                    chunk_end=chunk.end_line,
                    chunk_code=chunk.raw_code,
                    max_tokens=DEFAULT_CONFIG_D_PARAMS.context_token_budget,
                    token_counter=chunker.count_tokens,
                )

                user_prompt = build_config_d_user_prompt(
                    chunk,
                    static_section=static_section,
                    context_section=context_section,
                )

                model_target = (
                    getattr(getattr(client, "credentials", None), "model_id", None)
                    or DEFAULT_CONFIG_D_PARAMS.gateway_model_id
                )

                response_text, p_tok, c_tok = client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=DEFAULT_CONFIG_D_PARAMS.max_completion_tokens,
                    model_id=model_target,
                    thinking_type=DEFAULT_CONFIG_D_PARAMS.thinking_type,
                    thinking_effort=DEFAULT_CONFIG_D_PARAMS.thinking_effort,
                )

                total_p_tokens += p_tok
                total_c_tokens += c_tok
                raw_responses.append(response_text)

                cost_tracker.record_usage(
                    case_id=case.case_id,
                    chunk_index=chunk_idx,
                    prompt_tokens=p_tok,
                    completion_tokens=c_tok,
                    duration_seconds=time.monotonic() - start_time,
                    model_id=model_target,
                )

                parsed = parser.parse_response(
                    raw_text=response_text,
                    expected_file_path=case.target_file,
                    total_file_lines=chunk.total_lines,
                    chunk_start_line=chunk.start_line,
                    chunk_end_line=chunk.end_line,
                )
                case_findings.extend(parsed)

            deduped = deduplicate_findings(case_findings)
            duration = time.monotonic() - start_time
            telemetry = {
                "prompt_tokens": total_p_tokens,
                "completion_tokens": total_c_tokens,
                "cost_usd": cost_tracker.total_cost(),
                "raw_responses": raw_responses,
                "duration_seconds": duration,
            }
            return AuditStatus.SUCCESS, deduped, duration, telemetry
        except Exception as e:
            duration = time.monotonic() - start_time
            logger.warning("Config D failed for case %s: %s", case.case_id, e)
            return AuditStatus.FAILED, [], duration, {"error": str(e)}

    def run_configuration(
        self,
        config: str,
        case_ids: list[str] | None = None,
        run_id: str | None = None,
    ) -> ConfigurationRunOutput:
        """Execute a full benchmark evaluation for the requested configuration."""
        cfg = config.upper()
        rid = run_id or f"eval-{cfg.lower()}-{uuid.uuid4().hex[:8]}"

        # Select target cases
        cases_to_run = self.manifest.cases
        if case_ids:
            target_ids = {cid.upper() for cid in case_ids}
            cases_to_run = [c for c in cases_to_run if c.case_id.upper() in target_ids]

        predictions_by_case: dict[str, list[PredictedFinding]] = {}
        statuses_by_case: dict[str, str] = {}
        durations_by_case: dict[str, float] = {}
        provenance_by_case: dict[str, dict[str, Any]] = {}

        # 1. Check if running offline and frozen historical run should be loaded
        frozen_meta = None
        cost_usd = None
        if self.mode == "offline" and self.use_frozen_fixture_fallback:
            frozen_data = self._load_frozen_run(cfg)
            if frozen_data:
                logger.info("Loaded frozen historical benchmark results for Config %s", cfg)
                cases_data = frozen_data.get("cases", [])
                target_id_set = {c.case_id.upper() for c in cases_to_run}
                for c in cases_data:
                    cid = c["case_id"]
                    if cid.upper() not in target_id_set:
                        continue
                    # Parse raw findings into PredictedFinding
                    parsed_findings: list[PredictedFinding] = []
                    for f in c.get("findings", []):
                        try:
                            parsed_findings.append(PredictedFinding(**f))
                        except Exception:
                            pass
                    predictions_by_case[cid] = parsed_findings
                    statuses_by_case[cid] = c.get("execution_status", "success")
                    durations_by_case[cid] = float(c.get("duration_seconds", 0.0))
                    provenance_by_case[cid] = {
                        "source": ResultProvenance.FROZEN_HISTORICAL.value,
                        "status": statuses_by_case[cid],
                        "model": (frozen_data.get("metadata") or {}).get("model_display_name")
                        or (frozen_data.get("metadata") or {}).get("model_id")
                        or "Claude Sonnet 4.6",
                    }

                frozen_meta = frozen_data.get("metadata") or frozen_data.get("aggregate_metrics")
                cost_usd = (frozen_data.get("metadata") or {}).get("total_cost_usd")

        # 2. Fresh execution for any remaining cases (e.g. clean controls or live mode)
        remaining_cases = [c for c in cases_to_run if c.case_id not in predictions_by_case]

        # Pre-calculate Config A static findings if running Config C or D for remaining cases
        cached_static: dict[str, list[PredictedFinding]] = {}
        if cfg in ("C", "D"):
            frozen_a = self._load_frozen_run("A")
            if frozen_a:
                for c in frozen_a.get("cases", []):
                    cached_static[c["case_id"]] = [PredictedFinding(**f) for f in c.get("findings", [])]

        active_model_name = (
            getattr(getattr(self.api_client, "credentials", None), "model_id", "ag/claude-sonnet-4-6")
            if self.mode == "live"
            else "MockEvaluationLlmClient"
        )

        for case in remaining_cases:
            cid = case.case_id
            with tempfile.TemporaryDirectory(prefix=f"auditor-eval-{cid}-") as tmp_ws:
                ws_path = Path(tmp_ws)
                telemetry: dict[str, Any] = {}

                if cfg == "A":
                    status, findings, dur = self.run_case_config_a(case, ws_path)
                    prov_source = ResultProvenance.REAL_DETERMINISTIC.value
                    prov_model = "Ruff 0.16.10 + Semgrep CE 1.180.0"
                    cached_static[cid] = findings
                elif cfg == "B":
                    status, findings, dur, telemetry = self.run_case_config_b(case, ws_path)
                    prov_source = ResultProvenance.REAL_MODEL.value if self.mode == "live" else ResultProvenance.MOCK.value
                    prov_model = active_model_name
                elif cfg == "C":
                    if cid in cached_static:
                        s_findings = cached_static[cid]
                    else:
                        _, s_findings, _ = self.run_case_config_a(case, ws_path)
                        cached_static[cid] = s_findings
                    status, findings, dur, telemetry = self.run_case_config_c(case, ws_path, s_findings)
                    prov_source = ResultProvenance.REAL_MODEL.value if self.mode == "live" else ResultProvenance.MOCK.value
                    prov_model = active_model_name
                elif cfg == "D":
                    if cid in cached_static:
                        s_findings = cached_static[cid]
                    else:
                        _, s_findings, _ = self.run_case_config_a(case, ws_path)
                        cached_static[cid] = s_findings
                    status, findings, dur, telemetry = self.run_case_config_d(case, ws_path, s_findings)
                    prov_source = ResultProvenance.REAL_MODEL.value if self.mode == "live" else ResultProvenance.MOCK.value
                    prov_model = active_model_name
                else:
                    raise ValueError(f"Unsupported configuration: {cfg}")

                predictions_by_case[cid] = findings
                statuses_by_case[cid] = status.value if hasattr(status, "value") else str(status)
                durations_by_case[cid] = dur

                prov_entry: dict[str, Any] = {
                    "source": prov_source,
                    "status": statuses_by_case[cid],
                    "model": prov_model,
                    "duration_seconds": round(dur, 3),
                }
                if telemetry:
                    if "tokens" in telemetry:
                        prov_entry["tokens"] = telemetry["tokens"]
                    elif "prompt_tokens" in telemetry:
                        prov_entry["tokens"] = {
                            "prompt": telemetry["prompt_tokens"],
                            "completion": telemetry.get("completion_tokens", 0),
                        }
                    elif "chunk_telemetry" in telemetry:
                        p_t = sum(ct.get("tokens", {}).get("prompt", 0) for ct in telemetry["chunk_telemetry"])
                        c_t = sum(ct.get("tokens", {}).get("completion", 0) for ct in telemetry["chunk_telemetry"])
                        prov_entry["tokens"] = {"prompt": p_t, "completion": c_t}

                    if "cost_usd" in telemetry:
                        prov_entry["cost_usd"] = telemetry["cost_usd"]
                    elif "chunk_telemetry" in telemetry:
                        c_usd = sum(ct.get("cost_usd", 0.0) for ct in telemetry["chunk_telemetry"])
                        prov_entry["cost_usd"] = c_usd

                    if "raw_response" in telemetry:
                        prov_entry["raw_response"] = telemetry["raw_response"]
                    elif "raw_responses" in telemetry:
                        prov_entry["raw_responses"] = telemetry["raw_responses"]

                provenance_by_case[cid] = prov_entry

        # Compute total live cost if recorded in provenance
        total_live_cost = sum(
            entry.get("cost_usd", 0.0)
            for entry in provenance_by_case.values()
            if isinstance(entry, dict) and "cost_usd" in entry and entry.get("source") == ResultProvenance.REAL_MODEL.value
        )
        if total_live_cost > 0:
            cost_usd = total_live_cost

        return ConfigurationRunOutput(
            configuration=cfg,
            run_id=rid,
            mode=self.mode,
            predictions_by_case=predictions_by_case,
            statuses_by_case=statuses_by_case,
            durations_by_case=durations_by_case,
            provenance_by_case=provenance_by_case,
            cost_usd=cost_usd,
            metadata=frozen_meta,
        )

    def _resolve_case_code(self, case: ManifestCase, allow_placeholder: bool = False) -> str:
        """Extract authentic source code from repository or local fixture.

        Guarantees no silent substitution of generic placeholders unless explicitly opted in.
        """
        if case.fixture_path:
            fp = REPO_ROOT / case.fixture_path
            if fp.exists():
                return fp.read_text(encoding="utf-8")
        clean_fp = REPO_ROOT / "data" / "fixtures" / "clean_controls" / case.target_file
        if clean_fp.exists():
            return clean_fp.read_text(encoding="utf-8")

        try:
            bcase = case.to_benchmark_case()
            repo_path = resolve_case_repo_path(bcase)
            return extract_target_file_content(repo_path, case.commit_hash, case.target_file)
        except Exception as e:
            if not allow_placeholder:
                raise FileNotFoundError(
                    f"Target source code for case {case.case_id} ({case.target_file}) could not be "
                    f"resolved from local fixture or upstream repo: {e}"
                ) from e
            # Explicitly allowed fallback for unmaterialized dry-runs
            return (
                f"# Benchmark case {case.case_id} target file {case.target_file}\n"
                "def authenticate(user_token):\n"
                "    if not user_token:\n"
                "        return None\n"
                "    return {'status': 'authenticated', 'user': user_token}\n"
            )

    def _load_frozen_run(self, config: str) -> dict[str, Any] | None:
        """Load historical frozen benchmark results from data/results/."""
        file_map = {
            "A": FROZEN_RESULTS_DIR / "config_a_18_case_derived_run.json",
            "B": FROZEN_RESULTS_DIR / "config_b_pilot_run.json",
            "C": FROZEN_RESULTS_DIR / "config_c_pilot_run.json",
            "D": FROZEN_RESULTS_DIR / "config_d_pilot_run.json",
        }
        path = file_map.get(config.upper())
        if path and path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Could not read frozen run %s: %s", path, e)
        return None
