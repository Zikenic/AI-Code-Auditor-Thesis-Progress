# Week 1-2 Target Document
**Syllabus objective:** Khao sat; chot pham vi, nhom loi va ngon ngu; lap yeu cau, tieu chi danh gia.
(Survey tools; finalize scope, target bug categories & language; define requirements & evaluation criteria.)

**Window:** 07/09/2026 - 20/09/2026 | **Status:** In progress, closing out

---

## 1. Scope & Target Language
> Proposed in the outline, pending final confirmation (checklist item 1).

- Language: Python (small-to-medium web projects — FastAPI / Flask)
- Review Scope: Pull Requests on GitHub, via GitHub Actions webhook/workflow
- Model Strategy: Commercial/Open LLM via API — no fine-tuning/training
- **Confirmed?** [ ] No — [ ] Yes (date: ____)

## 2. Taxonomy & Target Bug Categories (CWE Mapping)
> To be finalized with supervisor (checklist item 2). Do not force a CWE mapping where none genuinely applies.

| # | Category | Candidate CWE(s) | Justification | Confirmed w/ Supervisor? |
|---|---|---|---|---|
| 1 | Boundary / conditional logic (off-by-one, null checks, NoneType) | TBD | | [ ] |
| 2 | Input validation & sanitization | TBD | | [ ] |
| 3 | SQL / ORM injection | TBD | | [ ] |
| 4 | Path traversal / unsafe file ops | TBD | | [ ] |
| 5 | Missing/broken authentication | TBD | | [ ] |
| 6 | Missing/broken authorization | TBD | | [ ] |

## 3. Tooling & Baseline Survey
> Checklist item 3. Findings go here; primary sources only, flag anything not backed by official docs.

### Ruff
- Linting capabilities: [TO FILL]
- AST-related capabilities: [TO FILL]
- Security-oriented rules: [TO FILL]
- Speed/caching: [TO FILL]

### Semgrep
- Python AST/pattern matching: [TO FILL]
- Security rules: [TO FILL]
- Custom rule creation: [TO FILL]
- CWE-related mappings: [TO FILL]
- CI integration: [TO FILL]

### Repo-level Context / RAG Approaches
- A. AST/symbol extraction — preserves / loses: [TO FILL]
- B. Structural graph (imports -> dependency graph -> call graph) — preserves / loses: [TO FILL]
- C. Semantic retrieval (embeddings + pgvector) — preserves / loses: [TO FILL]
- Cross-file call handling, symbol renaming, latency/token implications: [TO FILL]

### GitHub Actions / CI
- `pull_request` event behavior, token permissions, fork restrictions, secrets exposure, comment/review permissions: [TO FILL]

## 4. Benchmark Dataset Design (First Draft)
> Checklist item 4.

- Target: 100 cases minimum — 50 buggy / 50 clean
- Mix: single-file diffs + cross-file dependencies
- Split: 30% Dev / 70% Test, stratified, grouped by repo/family, locked once set

**Metadata schema per case:**
`case_id, repository, PR/commit, language, bug_class, CWE, changed_files, ground_truth_files, ground_truth_line_range, bug_description, pre_fix, post_fix, minimal_diff, verification_test, expected_detection`

**Sourcing plan:**
| Source type | Tool | Target count |
|---|---|---|
| Real bugs | BugsInPy / SWE-bench / SWE-Forge | [TO FILL] |
| Controlled synthetic (per category above) | SWE-smith | [TO FILL] |

**Ground truth rule:** every case needs an auditable chain (buggy commit -> documented defect -> reproducer/test -> fixed commit -> verification) or explicit supervisor sign-off — no tool-asserted bug counts on its own.

## 5. Evaluation Criteria & Metric Formulas
> Checklist item 5.

- Precision = TP / (TP + FP) — target >= 75%
- Recall = TP / (TP + FN) — target >= 60%
- F1 = 2 * (Precision * Recall) / (Precision + Recall)
- False Positive Rate = Clean PRs flagged / Total clean PRs
- Operational: Latency (Median, P95), token consumption, cost per PR
- 3x repeat runs per evaluation to capture LLM variance

---

## Output Deliverable A — Functional & Non-Functional Requirements Specification
> Draft here once Section 1 is confirmed. Each requirement: ID -> description -> rationale -> acceptance criteria -> verification method.

**Functional:** FR-01 PR Intake, FR-02 Repository Acquisition, FR-03 Static Analysis, FR-04 LLM Analysis, FR-05 Repository Context Retrieval, FR-06 Finding Aggregation, FR-07 GitHub Publication, FR-08 Audit Persistence, FR-09 Evaluation Mode — [ALL TO FILL]

**Non-functional:** NFR-01 Latency, NFR-02 Reproducibility, NFR-03 Security, NFR-04 Availability, NFR-05 Observability, NFR-06 Extensibility — [ALL TO FILL]

## Output Deliverable B — Dataset Design & Test Case List
> Populated from Section 4 once sourcing is complete. Final list lives here (or linked to a separate CSV once case count grows past what's readable in Markdown).

[TO FILL — case table or link to dataset file]

---

**Sign-off:** This document's Sections 1-2 require explicit supervisor confirmation before Week 3-4 architecture work begins (per AI_hand_off.md operating guideline #2).
