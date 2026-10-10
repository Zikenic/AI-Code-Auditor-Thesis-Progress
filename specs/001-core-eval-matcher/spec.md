# Feature Specification: Core Domain Contracts, Configuration Dispatch, and Offline Evaluation Matcher

**Feature ID**: `001-core-eval-matcher`  
**Status**: `Draft / In Implementation`  
**Date**: `2026-10-09`  
**Target Window**: `Week 3–4 (Continuing Implementation)`  

---

## 1. Executive Summary & Problem Statement
The central research inquiry of the AI Code Auditor thesis is evaluating how combining deterministic static analysis with repository-aware LLM review affects defect detection across four distinct configurations (A, B, C, D). 

To conduct reproducible empirical benchmarking and avoid circular coupling between the prediction engine and evaluation results, the project requires:
1. **Strong Domain Contracts**: Type-safe, validated domain models representing audit configurations, requests, findings, and ground-truth benchmark cases.
2. **Configurable Taxonomy & CWE Modeling**: Enforcement of the locked 6-category taxonomy (with governed expansion up to 8), mandatory `impact = functional | security` for Category 1, and pre-declared alternative CWE sets.
3. **Deterministic Evaluation Matcher**: An offline benchmark evaluation matcher that implements the locked $\pm 10$-line tolerance window, exact normalized file matching, and order-independent one-to-one defect consumption.
4. **Configuration Dispatch Engine**: A framework-agnostic orchestration core that enforces strict operational boundaries across Configurations A, B, C, and D.

---

## 2. User & Researcher Stories

- **US-1 (Benchmark Evaluator)**: As a thesis researcher, I want to evaluate predicted findings from an audit run against pre-declared ground-truth benchmark cases using exact normalized paths, acceptable CWE sets, and a uniform $\pm 10$-line tolerance, so that detection metrics (TP, FP, FN, Precision, Recall, F1) are objective, mathematically sound, and comparable across Configurations A–D.
- **US-2 (Order-Independent Matcher)**: As a thesis researcher, I want the evaluation matcher to use maximum-cardinality bipartite matching so that predictions and ground-truth defects are consumed one-to-one without dependency on list ordering or greedy selection flaws.
- **US-3 (Configuration Isolator)**: As an auditor core engine, I want configuration dispatch to strictly govern tool invocation (Config A: static only; Config B: LLM only; Config C: hybrid without repo context; Config D: hybrid with repo context), so that cross-configuration leakage is impossible.
- **US-4 (Domain Modeler)**: As a developer, I want Pydantic-validated models for findings, requests, results, and defects, so that invalid categories, missing coordinates, or missing Category 1 impacts are caught at runtime boundaries.

---

## 3. Functional Requirements

### FR-1.1: Core Domain Models
- `AuditConfiguration`: Enum with values `A`, `B`, `C`, `D`.
- `AuditRequest`: Represents PR audit target (`repository_id`, `pr_number`, `head_commit`, optional `base_commit`, `configuration`).
- `PredictedFinding`: Represents a single detected defect with `finding_id`, `detection_layer` (`deterministic_static` | `heuristic_llm`), `category_id`, `primary_cwe`, `alternative_cwes`, `file_path`, `start_line`, `end_line`, `severity`, `confidence`, `title`, `description`.
- `GroundTruthDefect`: Represents a verified defect with `defect_id`, `category_id`, `impact` (required if `category_id == 1`), `primary_cwe`, `acceptable_alternative_cwes`, `file_path`, `start_line`, `end_line`.
- `BenchmarkCase`: Represents an evaluation test case (`case_id`, `is_buggy`, list of `GroundTruthDefect`, target repo/commit).
- `AuditRunResult`: Represents execution output (`run_id`, `configuration`, `status`, list of `PredictedFinding`, execution metadata).

### FR-1.2: Taxonomy and Impact Validation
- The default active taxonomy contains Category IDs `1` through `6`.
- Category IDs `7` and `8` are permitted if and only if they are declared in the active approved taxonomy configuration; otherwise, validation fails with a descriptive error.
- Category 1 defects must declare `impact = "functional" | "security"`. For Categories 2–6, `impact` must be `None`.
- Primary CWE is mandatory. Alternative CWEs are supported as a pre-declared set (up to 3 total labels per case).

### FR-1.3: Range-Based Location & Evaluation Matcher
- **File Matching**: Exact normalized path matching (`posixpath.normpath`), stripping common repository prefixes and normalizing backslashes to forward slashes. No basename-only fallback.
- **CWE Matching**: Predicted finding satisfies CWE condition if `predicted.primary_cwe == gt.primary_cwe` OR `predicted.primary_cwe in gt.acceptable_alternative_cwes`.
- **Location Matching**:
  - Direct range overlap: $\max(s_{\text{GT}}, s_{\text{Pred}}) \le \min(e_{\text{GT}}, e_{\text{Pred}})$.
  - Proximity tolerance: Range intersection with $[\max(s_{\text{GT}} - 10, 1), e_{\text{GT}} + 10]$.
  - Findings with missing, zero, or negative line numbers fail location matching.
  - File-level findings without line numbers do not match localized defects.
- **One-to-One Matching**: Each ground-truth defect is consumed at most once using maximum-cardinality bipartite matching.
- **Scoring**:
  - Matched prediction = TP.
  - Unmatched prediction on buggy PR = FP.
  - Any prediction on clean PR = FP.
  - Unmatched ground-truth defect = FN.
  - **Metric Denominator Discipline**: $\text{Precision} = \frac{TP}{TP + FP}$, $\text{Recall} = \frac{TP}{TP + FN}$, $F_1 = \frac{2 \cdot P \cdot R}{P + R}$. When denominator is 0, metric evaluates to undefined / `None` (`N/A`) rather than silently returning 0.0 or 1.0.
  - **Operational Completion & Partial-Run Scoring Policy**:
    - Successful run contributes its normalized findings.
    - Failed, timed-out, or partially completed run contributes **no findings** to primary scoring (all early findings discarded; empty prediction set scored against ground truth, yielding 0 TPs, 0 FPs, and FNs equal to ground-truth defects).
    - Run completion status recorded separately: success, partial, failure, timeout.
    - Secondary success-only sensitivity analysis computed alongside primary operational results.
    - Supersedes earlier success-only proposal for primary scoring.

### FR-1.4: Configuration Dispatch Engine
- Abstract interfaces for:
  - `IStaticAnalysisEngine`: Executes deterministic tools (Ruff, Semgrep).
  - `ILlmReviewEngine`: Executes LLM review on code diffs.
  - `IRepoContextRetriever`: Retrieves cross-file symbols/context.
- Dispatch rules:
  - `Config A`: Invokes `IStaticAnalysisEngine` only.
  - `Config B`: Invokes `ILlmReviewEngine` only (passes diff without static findings or repo context).
  - `Config C`: Invokes `IStaticAnalysisEngine`, summarizes findings, passes to `ILlmReviewEngine`; zero repo context.
  - `Config D`: Invokes `IStaticAnalysisEngine`, `IRepoContextRetriever`, and `ILlmReviewEngine`.
- Framework independence: Core dispatch has no dependency on FastAPI, Flask, or web servers.

---

## 4. Non-Functional Requirements

- **NFR-1.1 (Determinism & Reproducibility)**: Given the same set of predictions and benchmark cases, the evaluation matcher must yield identical TP, FP, FN counts regardless of input array ordering.
- **NFR-1.2 (Type Safety & Validation)**: Domain models must use Pydantic v2 with strict type validation and explicit custom validators.
- **NFR-1.3 (Offline Isolation)**: The core evaluation matcher and configuration dispatcher must operate 100% offline without network calls, external API dependencies, or filesystem mutation.
- **NFR-1.4 (Test Coverage)**: Comprehensive unit tests covering normal matching, edge boundaries ($\pm 10$ vs $\pm 11$), multi-line findings, missing coordinates, clean PRs, and dispatch boundaries.
