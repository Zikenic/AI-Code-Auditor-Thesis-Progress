# Functional & Non-Functional Requirements Specification

## Document Information
- **Document Version**: Version 1.0 — Validated Methodology
- **Date**: 2026-09-25
- **Project**: Automated Code Review and Bug Detection System (AI Code Auditor)
- **Student**: Bùi Vạn Khải (MSSV: 24520719)
- **Supervisor**: ThS. Tran Thi Hong Yen
- **Institution**: University of Information Technology — VNU-HCM
- **Status**: VALIDATED DELIVERABLE — Core evaluation methodology, locked 6-category taxonomy, locked ±10 lines matching tolerance, and research target metrics finalized. Ready for test-case construction.

---

## 1. Introduction & System Context

The **AI Code Auditor** is an automated Pull Request auditing and defect detection system designed for Python web backends (FastAPI and Flask). The system integrates a deterministic static analysis layer (Python AST, Ruff, Semgrep) with a heuristic semantic analysis layer powered by Large Language Models (LLMs) augmented with repository-level context retrieval.

### Core Objectives
1. Automatically intake GitHub Pull Requests, acquire diffs, and inspect modified Python code.
2. Execute deterministic linters and intra-file security rules (Ruff, Semgrep).
3. Support configurable repository-context retrieval (including candidate structural and semantic retrieval mechanisms) without injecting unnecessary whole-repository code.
4. Synthesize, deduplicate, and publish actionable review findings back to the GitHub Pull Request.
5. Provide a controlled evaluation harness to rigorously benchmark four system configurations (Configs A, B, C, D) against a ground-truth dataset.

---

## 2. Requirements Specification Structure

Each requirement in this specification is documented according to the following testable schema:

| Field | Description |
| :--- | :--- |
| **ID** | Unique requirement identifier (`FR-xx` for functional, `NFR-xx` for non-functional). |
| **Requirement** | Clear, unambiguous, and testable normative statement ("The system shall..."). |
| **Rationale** | Engineering and architectural justification for the requirement. |
| **Preconditions / Inputs** | Necessary system state and input data required for execution. |
| **Expected Behavior / Output** | Observable, deterministic behavior and output data produced. |
| **Acceptance Criteria** | Concrete, verifiable conditions that must be satisfied. |
| **Verification Method** | Test method used for validation (Unit Test, Integration Test, Benchmark Inspection). |
| **Status / Notes** | Current implementation status and dependencies on open decisions. |

---

## 3. Functional Requirements

### FR-01: Pull Request Intake

| Field | Detail |
| :--- | :--- |
| **ID** | **FR-01** |
| **Requirement** | The system shall intake a GitHub Pull Request event, extract its identity and metadata, and acquire the unified pull request diff. |
| **Rationale** | The primary operational unit of code review in the thesis scope is the Pull Request. The system must reliably identify which repository, branch, and commits are being audited. |
| **Preconditions / Inputs** | GitHub `pull_request` event payload (webhook or CI environment variables) containing: repository full name (`owner/repo`), pull request number, head branch and commit SHA, base branch and commit SHA. |
| **Expected Behavior / Output** | Extracts PR identity; validates that the PR targets supported branches; fetches the unified diff using the GitHub REST API or local git revision comparison; extracts the list of modified, added, and deleted file paths. |
| **Acceptance Criteria** | 1. Successfully identifies PR number, head SHA, base SHA, and author.<br>2. Accurately extracts the list of changed files.<br>3. Generates a structured diff representation including changed line ranges and hunk offsets.<br>4. Rejects or skips non-PR triggers gracefully without failure. |
| **Verification Method** | Automated Unit & Integration Tests using synthetic and recorded GitHub PR webhook payloads. |
| **Status / Notes** | Draft — Aligned with established thesis review scope (GitHub PR review via GitHub Actions). |

---

### FR-02: Repository State Acquisition

| Field | Detail |
| :--- | :--- |
| **ID** | **FR-02** |
| **Requirement** | The system shall acquire the repository source files at the exact commit revision corresponding to the Pull Request head, ensuring the base revision history is accessible for diff comparisons. |
| **Rationale** | Static analysis tools and repository context retrieval engines require access to local source files and module trees to parse ASTs, resolve imports, and inspect caller/callee relationships. |
| **Preconditions / Inputs** | Valid repository access (via runner checkout or local clone); head commit SHA; base commit SHA. |
| **Expected Behavior / Output** | Clones or checks out the repository state at `head.sha`; configures git history depth (`fetch-depth: 0` or dual branch fetch) to enable `base...head` diff computation; makes local filesystem paths available to subsequent analysis stages. |
| **Acceptance Criteria** | 1. Working tree reflects the exact state of `head.sha`.<br>2. All Python source files modified in the PR exist on the local filesystem.<br>3. Local module resolution paths match repository root package structure.<br>4. Shallow clone limitations that prevent diff calculation are avoided. |
| **Verification Method** | CI Integration Test verifying git HEAD SHA and filesystem presence of modified files. |
| **Status / Notes** | Draft — Informs CI/CD runner checkout configuration (`actions/checkout@v4`). |

---

### FR-03: Deterministic Static Analysis

| Field | Detail |
| :--- | :--- |
| **ID** | **FR-03** |
| **Requirement** | The system shall execute deterministic static analysis tools (Ruff and Semgrep Community Edition) on the modified Python files and emit structured, machine-readable findings. |
| **Rationale** | Research package R1 established that Ruff provides near-instantaneous syntactic hygiene and basic smell detection, while Semgrep CE provides expressive intra-file AST pattern matching and taint tracking (`mode: taint`). Deterministic findings must be separated from LLM heuristic findings. |
| **Preconditions / Inputs** | Local checkout of modified Python files; Python runtime environment with `ruff` and `semgrep` installed; configured rule sets (Ruff default + Flake8-bandit rules; Semgrep security and framework registry rules). |
| **Expected Behavior / Output** | Executes Ruff (`ruff check --output-format json`) and Semgrep (`semgrep scan --config auto --json`); captures CLI outputs; parses tool findings into standardized internal finding objects (file, line range, rule ID, message, tool name); prevents runner failure on non-zero exit codes. |
| **Acceptance Criteria** | 1. Ruff and Semgrep execute against all changed Python files.<br>2. All emitted findings contain line-accurate location, rule ID, and finding message.<br>3. Findings carry an explicit tag: `detection_layer: deterministic_static`.<br>4. Execution finishes within CI runner time limits without unhandled crashes. |
| **Verification Method** | Automated Unit Tests on Python test fixtures with known syntax, Bandit, and Semgrep taint defects. |
| **Status / Notes** | Draft — Grounded in verified research package `R1_ruff_vs_semgrep.md`. |

---

### FR-04: LLM Semantic Analysis

| Field | Detail |
| :--- | :--- |
| **ID** | **FR-04** |
| **Requirement** | The system shall invoke a Large Language Model via an abstract API client to perform semantic code review on the PR diff and associated context, detecting complex logic, validation, and security defects. |
| **Rationale** | Static analysis tools are blind to cross-file semantic intent, complex business logic flaws, and dynamic framework behaviors. LLM review provides heuristic reasoning over code intent and edge cases. |
| **Preconditions / Inputs** | PR diff hunks; retrieved repository context (per active configuration); structured review prompt template; valid LLM API credentials configured securely in runtime environment. |
| **Expected Behavior / Output** | Formulates prompt containing code diff and contextual definitions; queries the LLM API; parses LLM response into structured finding objects; tags findings with `detection_layer: heuristic_llm`; records prompt tokens, completion tokens, model ID, and API call latency. |
| **Acceptance Criteria** | 1. Emits findings adhering to the system's structured finding schema.<br>2. Assigns each finding to one of the six working bug categories.<br>3. Handles API rate limits (HTTP 429), timeouts, and JSON parsing errors gracefully without pipeline termination.<br>4. Abstract client interface allows substituting model providers without altering review pipeline logic. |
| **Verification Method** | Mock API unit tests (verifying schema parsing and error handling) and live integration tests against standard evaluation cases. |
| **Status / Notes** | Draft — Scope constrained to commercial/open LLM API without fine-tuning (per manifesto). |

---

### FR-05: Configurable Repository Context Retrieval

| Field | Detail |
| :--- | :--- |
| **ID** | **FR-05** |
| **Requirement** | The system shall support configurable repository-context retrieval sufficient to evaluate the planned audit configurations, including configurations with and without repository-level context. |
| **Rationale** | The thesis benchmarks configurations that operate on isolated PR diffs (Configs B and C) against an augmented configuration that incorporates cross-file repository context (Config D). The retrieval subsystem must flexibly supply the required context level without prematurely selecting a single production retrieval architecture. |
| **Preconditions / Inputs** | Modified Python files; PR diff line ranges; repository source files; candidate retrieval mechanisms (such as AST symbol extraction, dependency/call graph traversal, or dense semantic search as evaluated in research package R2). |
| **Expected Behavior / Output** | Depending on the active evaluation configuration, either restricts context to the immediate diff and local file scope, or retrieves relevant cross-file definitions, dependencies, or references within a configurable prompt token budget. |
| **Acceptance Criteria** | 1. For configurations without repository context (Configs A, B, C): strictly isolates analysis to the PR diff and modified files.<br>2. For configurations with repository context (Config D): retrieves relevant cross-file context (using candidate AST, structural, or semantic mechanisms) bounded by a configurable token budget.<br>3. Supports comparative benchmarking across configurations without requiring pipeline re-architecture.<br>4. Handles dynamic or unresolved Python references gracefully without halting analysis. |
| **Verification Method** | Comparative integration tests verifying context isolation in Configs B/C and context enrichment in Config D against benchmark repositories. |
| **Status / Notes** | Draft Capability Requirement — Candidate mechanisms supported by research package `R2_repo_context_rag.md`; final production retrieval architecture remains open. |

---

### FR-06: Finding Aggregation & Deduplication

| Field | Detail |
| :--- | :--- |
| **ID** | **FR-06** |
| **Requirement** | The system shall aggregate findings from the deterministic static layer and the heuristic LLM layer, deduplicating overlapping alerts and normalizing findings into a unified schema. |
| **Rationale** | Running both static analysis and LLM analysis can produce duplicate or conflicting warnings for the same code line (e.g., both flagging a SQL concatenation). Developers must receive a cohesive, non-redundant review report. |
| **Preconditions / Inputs** | Raw finding lists from FR-03 (Static Analysis) and FR-04 (LLM Analysis). |
| **Expected Behavior / Output** | Matches findings by file path, overlapping line ranges, and defect category; merges duplicates into a single finding; preserves origin provenance (`detected_by: [ruff, llm]`); assigns standardized category and severity attributes. |
| **Acceptance Criteria** | 1. Zero duplicate findings on the identical file and line range for the same defect.<br>2. When static analysis and LLM both detect an issue, the aggregated finding cites both detection mechanisms.<br>3. Unmatched findings from either layer are preserved completely.<br>4. Output conforms strictly to the unified finding schema. |
| **Verification Method** | Automated Unit Tests with synthetic overlapping and disjoint finding sets. |
| **Status / Notes** | Draft — Essential for multi-layer audit pipeline synthesis. |

---

### FR-07: GitHub Publication

| Field | Detail |
| :--- | :--- |
| **ID** | **FR-07** |
| **Requirement** | The system shall publish aggregated audit findings back to the GitHub Pull Request as inline review comments and workflow summary annotations. |
| **Rationale** | Automated code review must meet developers where they work. Publishing findings directly on the PR diff allows immediate review and resolution during the code review cycle. |
| **Preconditions / Inputs** | Aggregated finding list (FR-06); PR metadata (FR-01); valid GitHub token (`GITHUB_TOKEN` or App token) with `pull-requests: write` permissions. |
| **Expected Behavior / Output** | Posts inline review comments on lines within the PR diff hunks via GitHub API; posts general PR summary comments for out-of-diff or repository-level findings; emits GitHub workflow commands (`::warning`, `::error`) for runner summary annotations; optionally emits SARIF for GitHub Code Scanning. |
| **Acceptance Criteria** | 1. Findings on modified lines appear as inline review comments on the PR "Files changed" tab.<br>2. Out-of-diff findings do not cause API rejections (HTTP 422 Unprocessable Entity) and are redirected to PR issue comments.<br>3. Published comments clearly indicate tool origin, defect category, and actionable remediation guidance.<br>4. Rate limits and duplicate comment re-posting across workflow re-runs are handled cleanly. |
| **Verification Method** | Integration tests against mock GitHub API and live test repository PRs. |
| **Status / Notes** | Draft — Grounded in GitHub Actions integration evidence from `R1_ruff_vs_semgrep.md`. |

---

### FR-08: Audit Run Persistence

| Field | Detail |
| :--- | :--- |
| **ID** | **FR-08** |
| **Requirement** | The system shall persist complete audit run records—including PR metadata, active configuration, raw tool findings, aggregated findings, execution metrics, and timestamps—to a relational database. |
| **Rationale** | Persistence is required for historical tracking, web UI visualization, audit trail reproducibility, and experimental evaluation analysis across benchmark runs. |
| **Preconditions / Inputs** | Audit execution data; database connection (PostgreSQL); completed finding aggregations and operational metrics. |
| **Expected Behavior / Output** | Stores audit session record in PostgreSQL database: repository ID, PR number, commit SHA, configuration ID (A/B/C/D), execution timestamps, duration, token usage, cost estimate, and individual finding records with file/line coordinates. |
| **Acceptance Criteria** | 1. All audit sessions generate a persistent record with a unique audit UUID.<br>2. Relational schema links individual findings to their parent audit session.<br>3. Failed or timed-out audit runs record error status without corrupting the database.<br>4. Supports querying audit history by repository, PR, and configuration. |
| **Verification Method** | Database integration tests verifying CRUD operations and relational integrity. |
| **Status / Notes** | Draft — Aligned with PostgreSQL database layer defined in manifesto. |

---

### FR-09: Experimental Evaluation Mode

| Field | Detail |
| :--- | :--- |
| **ID** | **FR-09** |
| **Requirement** | The system shall support an automated evaluation execution mode that runs controlled benchmark cases across the four configurations (A, B, C, D) and computes formal performance metrics against ground truth. |
| **Rationale** | The central research contribution of the thesis is comparing static analysis (A), isolated LLM review (B), hybrid review without repo context (C), and hybrid review with repo context (D) on a standardized Python benchmark. |
| **Preconditions / Inputs** | Benchmark dataset cases (locked dev/test split); ground-truth annotations (buggy/clean label, defect line range, target category); target configuration ID; evaluation run count (3x repeat). |
| **Expected Behavior / Output** | Executes the specified configuration against each benchmark case; compares emitted findings against ground truth; classifies predictions into True Positives (TP), False Positives (FP), and False Negatives (FN); computes Precision, Recall, F1 score, and False Positive Rate (FPR); records operational metrics (median/P95 latency, tokens, cost). |
| **Acceptance Criteria** | 1. Executes batch evaluation unattended across all assigned dataset cases.<br>2. Correctly applies locked detection matching criteria (matching file path, line range overlap or locked ±10 lines tolerance window, and correct category or pre-declared alternative CWE).<br>3. Accurately calculates Precision, Recall, F1, and FPR formulas from raw confusion matrix counts.<br>4. Computes mean and standard deviation across the 3x repeat runs to quantify LLM variance.<br>5. Emits a machine-readable evaluation report (JSON/CSV) suitable for thesis documentation. |
| **Verification Method** | Automated test suite verifying metric calculation logic against synthetic confusion matrices with known mathematical outcomes. |
| **Status / Notes** | Validated — Operationalizes the evaluation protocol from manifesto Section 8 and Section 5, Item 6. The finding-to-ground-truth matching rule is locked with a ±10 lines tolerance window, one-to-one matching, and pre-declared alternative CWE sets. Precision >= 75% and Recall >= 60% are validated non-binding research targets / empirical hypotheses, not pass/fail gates. |

---

## 4. Non-Functional Requirements

### NFR-01: Execution Latency

| Field | Detail |
| :--- | :--- |
| **ID** | **NFR-01** |
| **Requirement** | The system's automated audit pipeline shall execute within practical CI/CD runtime constraints, and its operational latency (median and P95) shall be recorded for every evaluation run. |
| **Rationale** | PR code review tools operate in CI/CD pipelines where excessive execution time delays developer feedback and blocks merge workflows. |
| **Acceptance Criteria** | 1. Deterministic static analysis (Ruff + Semgrep) must complete within a reasonable developer feedback window on small-to-medium PRs.<br>2. Pipeline records start, end, and elapsed times for intake, static analysis, context retrieval, LLM analysis, and publication.<br>3. Latency targets (median and P95) are measured experimentally across configurations A, B, C, and D during benchmark evaluation, rather than asserted as unmeasured assumptions. |
| **Verification Method** | Automated benchmarking harness recording millisecond timestamps and computing median/P95 latency across evaluation runs. |
| **Status / Notes** | Draft — Avoids fabricated latency targets; requires empirical measurement on thesis benchmark. |

---

### NFR-02: Evaluation Reproducibility & Variance Control

| Field | Detail |
| :--- | :--- |
| **ID** | **NFR-02** |
| **Requirement** | The evaluation procedure shall ensure experimental reproducibility across runs and quantify LLM stochastic variance through repeated trials. |
| **Rationale** | LLM responses exhibit stochastic variability. Thesis conclusions regarding the superiority of Configuration D over B or C must be statistically sound and reproducible. |
| **Acceptance Criteria** | 1. Evaluation runs use a fixed, version-controlled benchmark dataset with locked train/test splits.<br>2. Prompt templates, system instructions, and temperature parameters (e.g., `temperature: 0.0` or lowest supported) are strictly versioned.<br>3. Every evaluation configuration is evaluated through **3x repeat runs**.<br>4. Metrics report mean values and standard deviations across runs to capture variance. |
| **Verification Method** | Repeated execution of the automated evaluation suite against identical benchmark subsets, verifying metric tracking across runs. |
| **Status / Notes** | Draft — Directly fulfills manifesto Section 8 requirement for 3x repeat evaluations. |

---

### NFR-03: Security & Credential Protection

| Field | Detail |
| :--- | :--- |
| **ID** | **NFR-03** |
| **Requirement** | The system shall securely handle source code and protect all sensitive credentials, preventing secret leakage into logs, PR comments, or public repositories. |
| **Rationale** | Auditing tools process private source code and require access to LLM API keys and GitHub tokens. Credential exposure or unauthorized code transmission is a critical risk. |
| **Acceptance Criteria** | 1. API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `GITHUB_TOKEN`) must only be read from secure environment variables and never logged or exposed in finding text.<br>2. The `.env` file and tool-specific credential stores must remain strictly excluded via `.gitignore`.<br>3. Temporary cloned repository files and diff caches must be isolated in user-space or scratch directories and cleaned up after execution.<br>4. No repository source code may be transmitted to unauthorized external services beyond the designated LLM API provider. |
| **Verification Method** | Code inspection, static secret scanning (gitleaks / trufflehog rules), and automated log audit verifying absence of credential tokens. |
| **Status / Notes** | Draft — Strictly aligns with repository credential boundary rules. |

---

### NFR-04: Robustness & Fault Tolerance

| Field | Detail |
| :--- | :--- |
| **ID** | **NFR-04** |
| **Requirement** | The system shall handle tool errors, malformed syntax, network interruptions, and LLM API rate limits gracefully without unhandled crashes. |
| **Rationale** | CI pipelines encounter syntax errors in work-in-progress PRs and transient cloud API rate limits. The auditor must fail gracefully rather than crashing the CI runner. |
| **Acceptance Criteria** | 1. Syntax errors in incoming PR diffs (which fail Python AST parsing) are caught, logged, and reported as analysis limitations rather than crashing the system.<br>2. LLM API rate limits (HTTP 429) or transient errors (HTTP 503) trigger a configurable retry backoff policy before failing gracefully.<br>3. If one analysis layer encounters an error or timeout, available findings from operational layers are preserved, aggregated, and published with diagnostic failure warnings.<br>4. External API calls and tool processes are bounded by configurable timeout thresholds to prevent indefinite execution. |
| **Verification Method** | Fault-injection unit tests (mocking network failures, rate-limit responses, and corrupted Python AST inputs). |
| **Status / Notes** | Draft — Standard engineering resilience requirement. |

---

### NFR-05: Observability & Audit Traceability

| Field | Detail |
| :--- | :--- |
| **ID** | **NFR-05** |
| **Requirement** | The system shall record structured telemetry and execution logs for every audit session, enabling complete post-hoc diagnosis and evaluation verification. |
| **Rationale** | Academic evaluation requires an auditable chain of evidence linking input PRs, tool execution logs, model prompts, and final findings. |
| **Acceptance Criteria** | 1. Every audit session generates structured JSON logs containing: audit ID, PR number, commit SHAs, active configuration, stage execution durations, and tool exit codes.<br>2. Prompt token counts, completion token counts, and estimated financial costs are logged per LLM call.<br>3. Finding records retain complete attribution: originating tool/model, rule ID, prompt version, and exact file/line coordinates.<br>4. Logs are queryable by session UUID and PR identifier. |
| **Verification Method** | Inspection of generated telemetry logs during end-to-end audit runs. |
| **Status / Notes** | Draft — Supports academic traceability and evaluation reproducibility. |

---

### NFR-06: Modularity & Extensibility

| Field | Detail |
| :--- | :--- |
| **ID** | **NFR-06** |
| **Requirement** | The system shall support substitution of analysis, LLM, and retrieval components without requiring redesign of unrelated pipeline functions. |
| **Rationale** | LLM models, linter versions, and retrieval engines evolve rapidly. The thesis architecture must isolate components behind clear boundaries to enable comparative benchmarking across Configurations A, B, C, and D. |
| **Acceptance Criteria** | 1. The system shall support substituting or updating static analysis tools and rules without altering core pipeline orchestration.<br>2. The system shall support switching between different LLM API providers or models through abstract interfaces.<br>3. The system shall support configuring alternative repository context retrieval strategies across experimental runs.<br>4. Benchmark configurations (A, B, C, D) are defined declaratively via configuration settings rather than hardcoded pipeline branches. |
| **Verification Method** | Architecture inspection and integration tests demonstrating component substitution using mock implementations. |
| **Status / Notes** | Draft Capability Requirement — Defines modularity boundaries while leaving specific interface and class implementations to the Week 3–4 architecture phase. |

---

## 5. Scope Alignment & Final Methodological Decisions

The following items record the final, validated methodological decisions established for the thesis evaluation harness, alongside the high-level supervisor-confirmed scope:

> **Methodology Status**: The following decisions represent the **final / validated project methodology** for Week 1–2. The high-level direction (PR-based auditing, LLM API orchestration, 3 contribution pillars, Core MVP vs. Stretch AI Guardrail) is supervisor-confirmed. The technical evaluation methodology (6 locked categories, CWE representation policy, Category 1 impact attribute, dataset balance, locked ±10 lines matching rule, and research target classification) has been finalized for the thesis methodology. No further supervisor approval is required before proceeding to benchmark test-case construction.

1. **Target Language & Backend Scope**:
   - *Supervisor Confirmation*: High-level PR-based auditing and orchestration/integration of existing LLM APIs confirmed.
   - *Validated Implementation Choice*: Python web backends focused on small-to-medium FastAPI and Flask applications, and GitHub Actions PR review, are the validated technical choices for implementation.
   - *Status*: `Validated Project Implementation Choice`.
2. **Bug Taxonomy & Category Boundaries**:
   - *Final Methodology*: Initial taxonomy is locked to exactly six categories: (1) Boundary / conditional / logic (includes off-by-one and None/null logic flaws), (2) Input validation / sanitization, (3) SQL / ORM injection, (4) Path traversal / unsafe file ops, (5) Authentication, (6) Authorization.
   - *Scope Rule*: Six categories are the locked initial taxonomy for the thesis benchmark. If dataset construction naturally reveals a meaningful defect type that does not fit the existing taxonomy, expansion by up to two additional top-level categories is permitted, provided the addition is justified and documented. No unnecessary taxonomy expansion should occur.
   - *Status*: `Final Methodology — Locked Initial Taxonomy`.
3. **CWE Multi-Label Representation Strategy**:
   - *Final Methodology*: A test case may contain multiple CWE labels when necessary for accurate characterization of the defect (maximum 3 CWE labels per case; multi-CWE cases should remain uncommon and justified). A case may use a single primary CWE when that is sufficient. If retaining multiple CWE labels would create disproportionate evaluation complexity or prevent a reliable/reproducible scoring mechanism, use a single primary CWE instead. (Exploratory label-score closeness thresholds previously discussed are not a scoring formula; the authoritative project decision is the representation policy and single-label fallback rule).
   - *Status*: `Final Methodology — Representation Policy & Fallback Rule Locked`.
4. **Category 1 Scope Definition & Impact Attribute**:
   - *Final Methodology*: Retain the existing six category IDs without creating a seventh category. Category 1 cases are annotated with the orthogonal attribute `impact = functional | security` in the metadata schema to distinguish general functional correctness flaws from security-impacting logic defects in reporting and evaluation.
   - *Status*: `Final Methodology — Validated Decision`.
5. **Evaluation Metric Target Thresholds**:
   - *Final Methodology*: Precision $\ge 75\%$ and Recall $\ge 60\%$ are research targets / empirical hypotheses, NOT hard acceptance criteria or pass/fail gates. They must not be used to declare the thesis successful or unsuccessful by themselves. Benchmark reports will report measured Precision, Recall, F1, FPR, and operational metrics and interpret them empirically across Configurations A–D.
   - *Status*: `Final Methodology — Non-Binding Research Hypotheses`.
6. **Finding-to-Ground-Truth Matching Rule & Semantics**:
   - *Final Methodology (Locked Evaluation Rule)*: A predicted finding is a True Positive (TP) if and only if ALL three conditions hold:
     - *File match*: normalized predicted file path exactly matches normalized ground-truth file path (path-prefix differences resolved during normalization).
     - *Category / CWE match*: predicted category/CWE matches ground truth, OR belongs to an explicitly pre-declared acceptable alternative CWE set associated with that ground-truth case. (Alternative CWE sets must be defined prior to evaluation; no post-hoc mappings).
     - *Location match*: predicted line range overlaps ground truth, OR falls within the locked tolerance window around the ground-truth range.
     - *Locked Tolerance Window*: Set to exactly **±10 lines** applied uniformly across Configurations A–D (±5 lines is removed as an unresolved alternative).
     - *Edge Cases*: Multi-line findings match location via any line overlap. One-to-one matching: each ground-truth defect is consumed by at most one prediction. Additional unmatched predictions on buggy PRs = False Positive (FP), even if another prediction from the same PR already matched that defect. Any finding on a clean PR = False Positive (FP). A ground-truth defect with no prediction satisfying all three conditions = False Negative (FN). Secondary diagnostic metrics (exact line-match rate, line distance, category-only rate) remain optional diagnostics that do NOT alter primary counts.
   - *Status*: `Final Methodology — Locked Evaluation Rule (±10 Lines Tolerance)`.
