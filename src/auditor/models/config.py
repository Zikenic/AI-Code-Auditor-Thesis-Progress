"""Audit configuration enumeration."""

from enum import StrEnum


class AuditConfiguration(StrEnum):
    """The four comparative evaluation configurations of the AI Code Auditor thesis.

    - CONFIG_A: Static baseline (Ruff + Semgrep CE); no LLM review.
    - CONFIG_B: Isolated LLM review on PR diff; static analysis disabled; no repo context.
    - CONFIG_C: Hybrid review with static finding summaries provided to LLM; no repo context.
    - CONFIG_D: Full hybrid review with static finding summaries and repo-level context.
    """

    A = "A"
    B = "B"
    C = "C"
    D = "D"
