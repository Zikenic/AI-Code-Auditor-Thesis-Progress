"""Configuration B Audit Engine executing LLM-only code reviews.

Adheres strictly to:
- Project Documents/dataset/configuration_input_protocol.md
- Hierarchical chunking (Tier 1/2/3) under 16,000 source token budget
- Ground-truth blindness (INV-02, INV-09)
- FR-09 Partial-run scoring policy: if any chunk fails, case findings are discarded (0 emitted)
- Deterministic deduplication (INV-07)
- $20 budget ceiling guard
"""

from __future__ import annotations

import time
from typing import Any, Protocol

from auditor.llm.chunker import SourceChunk, SourceChunker
from auditor.llm.config import DEFAULT_CONFIG_B_PARAMS, ConfigBExecutionConfig
from auditor.llm.cost_tracker import CostTracker
from auditor.llm.deduplication import deduplicate_findings
from auditor.llm.parser import ConfigBResponseParser
from auditor.llm.prompt_builder import (
    assert_zero_answer_leakage,
    build_config_c_user_prompt,
    build_user_prompt,
    get_system_prompt,
)
from auditor.llm.static_formatter import format_static_findings_section
from auditor.models.finding import PredictedFinding
from auditor.models.result import AuditStatus


class ILlmApiClient(Protocol):
    """Protocol for LLM client communication (Anthropic, mock, or synthetic fixture)."""

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        model_id: str,
        thinking_type: str = "adaptive",
        thinking_effort: str = "medium",
    ) -> tuple[str, int, int]:
        """Return (completion_text, prompt_tokens, completion_tokens)."""
        ...


class ConfigBAuditEngine:
    """Configuration B Auditor: Zero-context semantic LLM code auditor."""

    def __init__(
        self,
        api_client: ILlmApiClient | None = None,
        config: ConfigBExecutionConfig = DEFAULT_CONFIG_B_PARAMS,
        chunker: SourceChunker | None = None,
        cost_tracker: CostTracker | None = None,
    ):
        self.api_client = api_client
        self.config = config
        self.chunker = chunker or SourceChunker(token_budget=config.source_token_budget)
        self.cost_tracker = cost_tracker or CostTracker(
            cost_per_input_million=config.cost_per_input_million,
            cost_per_output_million=config.cost_per_output_million,
            budget_ceiling_usd=config.budget_ceiling_usd,
        )
        self.parser = ConfigBResponseParser(model_name=config.model_id)

    def audit_source(
        self,
        raw_source: str,
        file_path: str,
        case_id: str = "CASE-AUDIT",
        forbidden_leakage_terms: list[str] | None = None,
        static_findings: list[dict[str, Any]] | None = None,
        config_name: str = "B",
    ) -> tuple[AuditStatus, list[PredictedFinding], dict[str, Any]]:
        """Audit target file source code through Configuration B or C pipeline.

        Returns (status, findings, metadata).
        Enforces partial-run failure policy: if any chunk fails or raises an error,
        all findings are discarded and status is set to FAILED/PARTIAL with 0 findings.
        """
        start_time = time.time()

        # Step 1: Chunk source code according to hierarchical policy
        chunks: list[SourceChunk] = self.chunker.chunk_source(raw_source, file_path)
        if not chunks:
            return AuditStatus.SUCCESS, [], {"total_chunks": 0, "duration": 0.0}

        system_prompt = get_system_prompt(config=config_name)
        case_findings: list[PredictedFinding] = []
        chunk_telemetry: list[dict[str, Any]] = []

        # If no API client is connected, this is an offline preflight check
        if self.api_client is None:
            return (
                AuditStatus.SUCCESS,
                [],
                {
                    "preflight_only": True,
                    "total_chunks": len(chunks),
                    "tier_used": chunks[0].tier,
                    "token_estimates": [c.token_estimate for c in chunks],
                },
            )

        # Step 2: Iterate through chunks
        for chunk in chunks:
            chunk_start = time.time()
            retained_static_count = 0
            omitted_static_count = 0
            static_section = ""

            if config_name.upper() == "C":
                static_section, retained_static_count, omitted_static_count = format_static_findings_section(
                    findings=static_findings or [],
                    chunk=chunk,
                    token_budget=getattr(self.config, "static_token_budget", 2000),
                )
                user_prompt = build_config_c_user_prompt(chunk, static_section=static_section)
            else:
                user_prompt = build_user_prompt(chunk)

            # Safeguard: Assert zero answer leakage
            assert_zero_answer_leakage(user_prompt, forbidden_leakage_terms)

            # Budget guard check
            if self.cost_tracker.would_exceed_ceiling(
                reserved_prompt_tokens=chunk.token_estimate + 1000,
                reserved_completion_tokens=2000,
            ):
                # Budget exceeded: discard and fail
                return (
                    AuditStatus.FAILED,
                    [],
                    {
                        "error": "Budget ceiling exceeded before chunk dispatch",
                        "chunks_completed": len(chunk_telemetry),
                    },
                )

            # Dispatch API call
            try:
                response_text, p_tokens, c_tokens = self.api_client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=self.config.max_completion_tokens,
                    model_id=self.config.gateway_model_id,
                    thinking_type=self.config.thinking_type,
                    thinking_effort=self.config.thinking_effort,
                )
            except Exception as e:
                # FR-09: Partial-Run Scoring Policy: Discard all findings on any chunk failure
                return (
                    AuditStatus.FAILED,
                    [],
                    {
                        "error": f"API call failed on chunk {chunk.chunk_index}: {str(e)}",
                        "failed_chunk": chunk.chunk_index,
                        "total_chunks": len(chunks),
                    },
                )

            chunk_duration = time.time() - chunk_start

            # Track cost
            cost_rec = self.cost_tracker.record_usage(
                case_id=case_id,
                chunk_index=chunk.chunk_index,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                duration_seconds=chunk_duration,
                model_id=self.config.model_id,
            )

            chunk_telemetry.append(
                {
                    "chunk_index": chunk.chunk_index,
                    "tokens": {"prompt": p_tokens, "completion": c_tokens},
                    "cost_usd": cost_rec.cost_usd,
                    "duration_seconds": cost_rec.duration_seconds,
                    "raw_response": response_text,
                    "static_findings_retained": retained_static_count,
                    "static_findings_omitted": omitted_static_count,
                }
            )

            # Parse and validate response
            try:
                chunk_findings = self.parser.parse_response(
                    raw_text=response_text,
                    expected_file_path=file_path,
                    total_file_lines=chunk.total_lines,
                    chunk_start_line=chunk.start_line,
                    chunk_end_line=chunk.end_line,
                )
                case_findings.extend(chunk_findings)
            except Exception as e:
                # Parsing failed on this chunk: enforce partial-run discard
                return (
                    AuditStatus.FAILED,
                    [],
                    {
                        "error": f"Output parsing failed on chunk {chunk.chunk_index}: {str(e)}",
                        "failed_chunk": chunk.chunk_index,
                    },
                )

        # Step 3: Deterministic deduplication across chunks (INV-07)
        final_findings = deduplicate_findings(case_findings)
        total_duration = time.time() - start_time

        telemetry = {
            "total_chunks": len(chunks),
            "tier_used": chunks[0].tier,
            "raw_findings_count": len(case_findings),
            "deduplicated_findings_count": len(final_findings),
            "total_duration_seconds": round(total_duration, 3),
            "chunk_telemetry": chunk_telemetry,
        }

        return AuditStatus.SUCCESS, final_findings, telemetry
