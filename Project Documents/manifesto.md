# AI Code Auditor — Manifesto (System Design)

## 1. What This Is
Automated Code Review and Bug Detection System (AI Code Auditor) — a PR audit pipeline that combines deterministic static analysis with LLM-based semantic review, benchmarked against ground-truth Python bug/PR pairs.

- Vietnamese title: He thong review ma nguon va phat hien loi tu dong (AI Code Auditor)
- Student: Bùi Vạn Khải (MSSV: 24520719)
- Supervisor: ThS. Tran Thi Hong Yen
- Institution: Truong Dai hoc Cong nghe Thong tin - DHQG TP.HCM
- Duration: 07/09/2026 - 26/12/2026 (16 weeks)

## 2. Core Problem
Reviewing Pull Requests spanning multiple files requires understanding function call hierarchies, data flow, and business logic. Static analysis handles deterministic rules; LLMs (supplied with repo-level context) analyze complex logic and security concerns.

## 3. Key Objectives & Supervisor-Confirmed Contribution Pillars

> Supervisor confirmation: project direction and MVP/Advanced scope confirmed in supervisor email provided by the student.

The project's core contribution directions are formally confirmed around three pillars:
1. **Hybrid Audit** — combine static analysis (AST/Linter) with LLM analysis.
2. **Repo-level Context** — use Code Graph / Repo RAG so analysis can use repository-wide context rather than isolated files.
3. **Quantitative Evaluation** — build a benchmark based on CWE/OWASP and evaluate with Precision, Recall, and false-positive rate.

### Pipeline Scope & Deliverables
- **Core MVP**: Automated logic and security bug testing on Git Pull Requests (Intake -> Hybrid Analysis -> Aggregation -> Publish).
- **Evaluation Harness**: Benchmark 4 configurations (A/B/C/D) measuring Precision, Recall, F1, FPR, latency, tokens, cost.
- **Advanced / Stretch Direction**: AI Guardrail for checking AI-generated code against project standards (confirmed as an advanced stretch goal, deferred outside the Core MVP).

## 4. System Architecture

> Architecture baseline approved and implemented: [`architecture/system_architecture.md`](architecture/system_architecture.md)

```
PR Event (GitHub Webhook HMAC-SHA256 / API Request)
  |
  v
Intake & Idempotency Layer (X-GitHub-Delivery deduplication & Atomic DB Persistence)
  |
  v
Checkout & Revision Manager (head revision, base diff)
  |
  +---> [Config A, C, D] Deterministic Static Analysis (Ruff + Semgrep CE) --+
  |                                                                           |
  +---> [Config D] Repo Context Engine (AST Symbols + Repository Index) ------+
  |                                                                           |
  +---> [Config B, C, D] LLM Semantic Review (Prompt + Diff + Context) -------+
                                                                              |
                                                                              v
                                                          Finding Normalizer & Deduplicator
                                                                              |
                                                                              +---> Physical DB Persistence (SQLite WAL / PostgreSQL)
                                                                              +---> GitHub PR Review Publisher (Prod)
                                                                              +---> Benchmark Metric Matcher (Eval)
```


## 5. Tech Stack
| Layer | Choice |
|---|---|
| Backend & Worker | Python (FastAPI approved and implemented; in-process BackgroundTasks prototype) |
| Frontend UI | React (deferred) |
| Database | SQLite physical database with WAL mode (PRAGMA journal_mode=WAL) implemented; PostgreSQL planned for production |
| Static Analysis | Python AST, Ruff 0.16.10, Semgrep CE 1.180.0 |
| Tokenizer / Accounting | Official Anthropic Messages API (`/v1/messages/count_tokens` with model `ag/claude-sonnet-4-6`) |
| Benchmark Dataset | 100-Case Ground-Truth Benchmark (50 Defective + 50 Clean Controls; 100% locally runnable) |
| CI/CD & Deploy | GitHub Actions, Docker |
| LLM Integration | Third-party LLM API (model chosen after baseline testing) |
| Standards/Taxonomy | CWE, OWASP Benchmark |

## 6. Benchmark Configurations
| Config | Description |
|---|---|
| A | Static analysis alone |
| B | LLM alone (diff + in-file context) |
| C | Hybrid Audit, no repo-wide context |
| D | Hybrid Audit + Repo-level Context |

### Development Pilot Scope vs. Production PR Review Objective
- **Production System Objective (Unchanged)**: The primary engineering objective of the thesis remains an automated Pull Request auditing pipeline that analyzes proposed code modifications (PR diff hunks) in CI/CD.
- **17-Case Development Pilot Scope (Approved Phase 3B.4 Decision)**: To ensure rigorous, direct comparability across Configurations A–D on the existing 17 ground-truth-verified pilot cases (where authentic historical bug-introducing PR diffs are unavailable in Git history), the controlled development pilot is formally approved as a **Whole-File / Component Audit** against the authentic pre-fix snapshot $C_{buggy}$.
- **Final PR-Specific Benchmark Evaluation (Still Open)**: Evaluating Configurations B–D on authentic PR-diff hunks remains an open requirement that will be addressed during final benchmark curation ($\ge 100$ cases) via a defensible, non-circular input construction method. The thesis is not redefined as a whole-file auditor.

## 7. Bug Taxonomy & CWE Representation (Final Validated Methodology)
| Category | Candidate CWE Alignment (`CWE_taxonomy.md`) | Status |
|---|---|---|
| Boundary / conditional logic (off-by-one, null checks, NoneType) | CWE-193, CWE-476, CWE-754, CWE-670 | Locked (Category 1) |
| Input validation & sanitization | CWE-20, CWE-116, CWE-1287 | Locked (Category 2) |
| SQL / ORM injection | CWE-89, CWE-943 | Locked (Category 3) |
| Path traversal / unsafe file ops | CWE-22, CWE-73, CWE-434 | Locked (Category 4) |
| Missing/broken authentication | CWE-306, CWE-287, CWE-347 | Locked (Category 5) |
| Missing/broken authorization | CWE-862, CWE-639, CWE-863 | Locked (Category 6) |

- **Locked Initial Taxonomy**: Exactly six categories above. If dataset construction naturally reveals a meaningful defect type that does not fit the existing taxonomy, expansion by up to two additional top-level categories is permitted, provided the addition is justified and documented.
- **Category 1 Impact Attribute**: Retains a single category with metadata `impact = functional | security` to distinguish functional correctness from security logic flaws.
- **CWE Representation Policy**: Maximum 3 CWE labels per case when necessary and justified; fallback to single primary CWE if multi-label scoring creates disproportionate complexity.

## 8. Evaluation Targets & Metrics
- **Primary TP Matching Rule (Locked)**: A prediction is a True Positive (TP) iff: (1) normalized file path matches exactly, (2) category/CWE matches ground truth or pre-declared acceptable alternative CWE set, and (3) line range overlaps or falls within locked tolerance of **±10 lines**.
- **Edge Cases**: 1-to-1 matching; extra unmatched predictions on buggy PRs = False Positive (FP); any finding on clean PR = False Positive (FP); unconsumed defect = False Negative (FN).
- Precision = TP / (TP + FP) (research target >= 75%; empirical hypothesis, not a hard pass/fail requirement)
- Recall = TP / (TP + FN) (research target >= 60%; empirical hypothesis, not a hard pass/fail requirement)
- F1 = 2 * (P * R) / (P + R)
- FPR = Clean PRs flagged / Total clean PRs
- Operational: latency (median, P95), token count, cost per PR
- 3x repeat runs per evaluation to measure LLM variance

## 9. Dataset Design Principles
- Minimum 100 cases (floor, no fixed ceiling): 50 buggy / 50 clean baseline target, mix of single-file and cross-file diffs
- Category representation approximately balanced (within 10 cases across categories where practical)
- Split: 30% dev / 70% test, stratified and locked, grouped by repo/family
- Metadata schema: case_id, repository, PR/commit, language, bug_class, CWE, impact, changed_files, ground_truth_files, ground_truth_line_range, bug_description, pre_fix, post_fix, minimal_diff, verification_test, expected_detection
- Real bugs (via BugsInPy / SWE-bench / SWE-Forge) preferred; synthetic (via SWE-smith) used to fill gaps in underrepresented categories
- Every case needs an auditable chain: buggy commit -> documented defect -> reproducer/test -> fixed commit -> verification (or explicit supervisor sign-off)

## 10. Non-Negotiables
- Static analysis = deterministic layer; LLM = heuristic layer — never conflate the two in reporting.
- The project relies on an existing LLM API and focuses on orchestration/integration rather than developing or training a model (supervisor confirmed).
- The Core MVP boundary is PR-based automated detection/testing of logic and security bugs; AI Guardrail is an Advanced / stretch direction (supervisor confirmed).
- Research tools (e.g. GPT Researcher) produce evidence only — they never decide scope, bug categories, requirements, or ground truth.
- No dataset case counts as ground truth without an auditable chain or supervisor validation.
- No fabricated performance numbers — only experimentally measured ones get reported.
- Any research/dataset-generation tooling (GPT Researcher, Spec Kit, SWE-smith, SWE-Forge) stays OUT of the production system architecture — dev tooling only.

## 11. Out of Scope (for now)
- Developing, training, or fine-tuning an LLM (focus is orchestration/integration via third-party LLM API; supervisor confirmed)
- Non-Python languages (working assumption)
- AI Guardrail extension (confirmed as an Advanced / stretch direction; deferred outside Core MVP)
