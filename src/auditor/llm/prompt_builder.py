"""Prompt assembly and ground-truth leakage guard for Configuration B."""

from __future__ import annotations

import re
from pathlib import Path

from auditor.llm.chunker import SourceChunk

REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPTS_DIR = REPO_ROOT / "Project Documents" / "prompts"
SYSTEM_PROMPT_PATH = PROMPTS_DIR / "config_b_prompt_v1.md"


CONFIG_C_SYSTEM_PROMPT_PATH = PROMPTS_DIR / "config_c_prompt_v1.md"
CONFIG_D_SYSTEM_PROMPT_PATH = PROMPTS_DIR / "config_d_prompt_v1.md"


def get_system_prompt(config: str = "B") -> str:
    """Extract system prompt markdown block from authoritative prompt specification."""
    cfg = config.upper()
    if cfg == "D":
        path = CONFIG_D_SYSTEM_PROMPT_PATH
    elif cfg == "C":
        path = CONFIG_C_SYSTEM_PROMPT_PATH
    else:
        path = SYSTEM_PROMPT_PATH

    if path.exists():
        text = path.read_text(encoding="utf-8")
        match = re.search(r"## 1\. System Prompt\s+```text\s+(.*?)\s+```", text, re.DOTALL)
        if match:
            return match.group(1).strip()

    # Fallback to embedded canonical system prompt
    return (
        "You are an expert security auditor and software verification engine conducting a rigorous "
        "code review of Python source code.\n"
        "Your task is to analyze the provided target code chunk and identify concrete bugs, vulnerabilities, "
        "or functional logic defects across the locked 6 categories."
    )


def build_user_prompt(chunk: SourceChunk) -> str:
    """Build user prompt for Configuration B (zero-context baseline)."""
    return (
        f"Please perform a security and defect audit of the following Python source code:\n\n"
        f"{chunk.rendered_text}\n"
        f"Identify all concrete security vulnerabilities and functional logic defects in this code. "
        f"Return your audit results exclusively as a valid JSON object matching the required schema."
    )


def build_config_c_user_prompt(chunk: SourceChunk, static_section: str = "") -> str:
    """Build user prompt for Configuration C (static-augmented)."""
    if static_section and static_section.strip():
        middle_block = f"\n{static_section.strip()}\n\n"
    else:
        middle_block = "\n"

    return (
        f"Please perform a security and defect audit of the following Python source code:\n\n"
        f"{chunk.rendered_text}"
        f"{middle_block}"
        f"Identify all concrete security vulnerabilities and functional logic defects in this code. "
        f"Return your audit results exclusively as a valid JSON object matching the required schema."
    )


def build_config_d_user_prompt(chunk: SourceChunk, static_section: str = "", context_section: str = "") -> str:
    """Build user prompt for Configuration D (hybrid static + repository context)."""
    blocks = [chunk.rendered_text]
    if static_section and static_section.strip():
        blocks.append(static_section.strip())
    if context_section and context_section.strip():
        blocks.append(context_section.strip())

    joined_content = "\n\n".join(blocks)
    return (
        f"Please perform a security and defect audit of the following Python source code:\n\n"
        f"{joined_content}\n\n"
        f"Identify all concrete security vulnerabilities and functional logic defects in this code. "
        f"Return your audit results exclusively as a valid JSON object matching the required schema."
    )


def assert_zero_answer_leakage(prompt_text: str, forbidden_terms: list[str] | None = None) -> None:
    """Assert INV-09: prompt contains zero forbidden advisory, CVE, fix commit, or defect locus terms."""
    if not forbidden_terms:
        return

    for term in forbidden_terms:
        if term and term.strip() and term.lower() in prompt_text.lower():
            raise ValueError(f"CRITICAL: Answer leakage detected in prompt text! Forbidden term: '{term}'")
