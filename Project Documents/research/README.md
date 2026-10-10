# Thesis Research Workflow Guide

## 1. Intended Workflow

```text
AG
 ↓
GPT Researcher
 ↓
raw research report + source trail
 ↓
Claude independent verification
 ↓
verified findings
 ↓
Student decision
 ↓
week1-2_target.md
```

## 2. Core Operational Rules

1. **Evidence Gathering Only**: GPT Researcher gathers evidence and source citations from literature, official documentation, and technical sources. It **never** decides thesis scope, bug categories, architecture, or ground truth.
2. **Independent Verification**: Claude acts as an independent verifier. It checks claims, verifies that primary source links and citations are genuine and accurate, tests reproducibility where applicable, and flags discrepancies.
3. **Final Thesis Authority**: The student (Bui Van Khai) and supervisor (ThS. Tran Thi Hong Yen) make all final decisions regarding thesis scope, methodology, taxonomy, and system architecture.
4. **Separation of Artifacts**: Research artifacts (in this `research/` directory) remain strictly distinct from official thesis targets, requirements, and decisions.
5. **No Unsupported Claims**: Unsupported, vague, or speculative claims from AI summaries must never be promoted into official thesis documents (`week1-2_target.md` or `manifesto.md`).
6. **Empirical Measurements Only**: Real performance, accuracy, and latency numbers must come from controlled experimental measurements on benchmark datasets, never from research reports or LLM speculation.

## 3. Research Topic Tracks

- `R1_ruff_vs_semgrep.md` — Survey of Ruff and Semgrep capabilities, AST/pattern matching, rule ecosystems, and CI integration.
  - **Status**: VERIFIED
  - **Primary GPT Researcher run**: FAILED (missing credentials)
  - **Fallback research method**: Direct primary-source research
  - **Audit & Closure**: COMPLETED (Audited against official Astral, Semgrep, and GitHub documentation; CI/CD integration section added; citation URLs updated)
  - **Independent verification**: Claude (Verified with corrections applied; closed)
- `R2_repo_context_rag.md` — Survey of repository-level context retrieval strategies (AST symbol extraction, dependency/call graphs, vector embeddings + pgvector).
  - **Status**: AUDITED & VERIFIED WITH CORRECTIONS
  - **Research Date**: 2026-09-25
  - **Primary GPT Researcher run**: SUCCEEDED (Gemini 3.8 Flash + DuckDuckGo)
  - **Citation Integrity Audit**: COMPLETED (Fabricated arXiv IDs and unverified blogs removed; genuine AACR-Bench and DyRetriever metadata corrected)
  - **Independent verification**: Claude (Pending formal sign-off)
- `R3_cwe_taxonomy.md` / `CWE_taxonomy.md` — Authoritative candidate CWE mappings, justifications, and boundaries for the 6 target bug categories.
  - **Status**: RESEARCH COMPLETE — AWAITING SUPERVISOR REVIEW
  - **Research Date**: 2026-09-25
  - **Research Method**: Authoritative standards research (MITRE CWE official definitions, NIST SP 800-53, OWASP Top 10 / API Top 10)
  - **Independent verification**: Claude (Pending verification)
  - **Thesis Authority**: Candidate evidence only; final taxonomy subject to supervisor approval.
- `R4_benchmark_methodology.md` — Benchmark dataset curation, sourcing chains (SWE-bench, BugsInPy, SWE-Forge, SWE-smith), schema, and evaluation metric formulas. [Status: NOT STARTED]
