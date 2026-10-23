# Week 5–6 Thesis Deliverables Acceptance and Verification Report

> **Audit Status**: PASS (All 3 Deliverables Accepted with Verified Implementation and Tests)  
> **Evaluation Date**: 2026-10-24  
> **Baseline Commit**: `ffbbe76`  
> **Working Branch**: `fix/week5-6-final-acceptance-gaps`  
> **Target Scope**: 100-Case Benchmark Provenance & Execution, Tokenizer Fidelity, and Backend/Webhook Workflow  
> **Live Inference Spend**: **$0.00** (Zero completion tokens generated)  

---

## 1. Executive Summary

This report delivers the comprehensive independent acceptance audit and gap-closure verification for the AI Code Auditor thesis Week 5–6 deliverables. Every finding, census figure, and architectural boundary reported herein is verified by automated regression tests and verifiable disk artifacts.

### Deliverable Acceptance Scorecard

| Deliverable | Status | Registered Count | Runnable Count | Key Verification Proof |
| :--- | :---: | :---: | :---: | :--- |
| **1. 100-Case Benchmark** | **PASS** | 100 | **100** | Full 50 buggy and 50 clean controls resolve to authentic code on disk. 18 upstream repository snapshots materialized at exact vulnerable commits with SHA256 integrity. Corrected provenance: 82 synthetic/handcrafted, 18 upstream. Zero placeholder fallbacks. |
| **2. Real Tokenizer Measurement** | **PASS** | N/A | N/A | Local gateway `POST /v1/messages/count_tokens` natively measures complete rendered prompt (system + user + static findings + context + schema) in a single request. Exact model identifier parity (`ag/claude-sonnet-4-6`). Tiktoken and character estimators explicitly marked heuristic; strict execution raises on error without silent downgrade. |
| **3. Backend API, DB & Webhooks** | **PASS** | N/A | N/A | FastAPI backend across 7 routers. Physical SQLite WAL persistence proven across true OS subprocess termination and restart. Webhook HMAC-SHA256 constant-time verification, `X-GitHub-Delivery` idempotency, atomic DB persistence, failure rejection, and retrievability via `GET /api/v1/audits/{id}` verified. Workspace path traversal restricted (system temp untrusted). Documented prototype in-process execution model. |

---

## 2. Deliverable 1: Benchmark Provenance, Census, and Reproducibility

### 2.1 Provenance Reconciliation

A rigorous audit of git history (`feat/benchmark-clean-controls`, commit `0cae2d8`) and dataset documents established that the prior report's claim ("64 synthetic and 36 real-world/pilot") was flawed because it mistakenly classified the original 18 clean controls as "real-world" simply because they were part of the 36-case pilot evaluation. 

In reality:
1. **Upstream Repository Snapshots (18 Cases)**: The 18 historical defective cases (`CAND-0001, 0002, 0006, 0007, 0008, 0009, 0014, 0015, 0017, 0019, 0020, 0021, 0025, 0026, 0027, 0031, 0032, 0033`) are genuine real-world vulnerabilities from open-source repositories (`tornadoweb/tornado`, `tiangolo/fastapi`, `scrapy/scrapy`, `django/django`, `pallets/werkzeug`, `aio-libs/aiohttp`, `paramiko/paramiko`, etc.).
2. **Synthetic Buggy Fixtures (32 Cases)**: Hand-designed deterministic fixtures in `data/fixtures/buggy_cases/` (`cand_0003`, `cand_0004`, `cand_0005`, `cand_0010`..`cand_0050`) created to complete the 50 defective cases across categories 1–6.
3. **Handcrafted Clean Control Fixtures (18 Cases)**: Hand-crafted clean fixtures in `data/fixtures/clean_controls/` (`ctrl_0001` through `ctrl_0018`), paired with the problem domains of the 18 pilot cases. These are handcrafted local fixtures, NOT upstream repository checkouts (`synthetic: true`, `source_type: "handcrafted_clean_fixture"`).
4. **Synthetic Clean Control Fixtures (32 Cases)**: Hand-designed clean fixtures in `data/fixtures/clean_controls/` (`ctrl_0019` through `ctrl_0050`), paired with `CAND-0019`..`CAND-0050` (`synthetic: true`, `source_type: "synthetic_fixture"`).

```text
+--------------------------------------------------------------------------------------------------+
|                                    100-CASE BENCHMARK CENSUS                                     |
+------------------------------------------------+-------------------------------------------------+
|              50 DEFECTIVE CASES                |               50 CLEAN CONTROLS                 |
+-----------------------+------------------------+------------------------+------------------------+
| Upstream Snapshots    | Synthetic Buggy        | Handcrafted Clean      | Synthetic Clean        |
| (18 cases)            | (32 cases)             | (18 cases)             | (32 cases)             |
| CAND-0001, 0002...    | CAND-0003, 0004...     | CTRL-0001..CTRL-0018   | CTRL-0019..CTRL-0050   |
| synthetic: false      | synthetic: true        | synthetic: true        | synthetic: true        |
| source: upstream repo | source: local fixture  | source: local fixture  | source: local fixture  |
+-----------------------+------------------------+------------------------+------------------------+
| Total Externally Sourced: 18 Cases (18%)       | Total Synthetic/Handcrafted: 82 Cases (82%)     |
| Total Registered: 100 Cases                    | Total Reproducibly Evaluated Locally: 100 Cases |
+------------------------------------------------+-------------------------------------------------+
```

### 2.2 Materialization of the 18 Upstream Snapshots

To eliminate dependence on external git checkouts while avoiding silent generic placeholder fallbacks:
- Each target file for the 18 historical vulnerable commits was fetched directly from GitHub at its exact recorded commit SHA (e.g. `2ca8821d006f6693f920a4b183a3a7c985a5c8ad` for Tornado, `210af1fd3dc0f612a08fa02a0cb3f5adb81e5bfb` for FastAPI).
- Stored under `data/fixtures/upstream_snapshots/{case_id}/{target_file}` with exact UNIX LF line endings matching the upstream commit.
- A cryptographic provenance record (`provenance.json`) was generated for each case containing `case_id`, `repository`, `commit_hash`, `target_file`, `source_url`, `sha256`, and `line_ranges`.
- Every ground-truth defect locus was verified against the downloaded file, extracting valid, non-empty code matching the vulnerability annotations.
- `runner._resolve_case_code(case, allow_placeholder=False)` resolves all 100 cases to authentic source code on disk. Zero placeholder stubs are returned.

---

## 3. Deliverable 2: Model-Compatible Token Counting Fidelity

### 3.1 Gateway Endpoint & Model Parity

- **Endpoint**: The official Anthropic Messages token counting route `POST /v1/messages/count_tokens` is exposed by the local gateway.
- **Model Parity**: The token counter submits `model: "ag/claude-sonnet-4-6"` (or the configured `gateway_model_id`), matching the inference engine's target model identity.
- **Protocol**: Verified against the gateway schema:
  ```json
  {
    "model": "ag/claude-sonnet-4-6",
    "system": "<SYSTEM_PROMPT>",
    "messages": [
      {
        "role": "user",
        "content": "<COMPLETE_RENDERED_PROMPT>"
      }
    ],
    "thinking": {"type": "adaptive"},
    "output_config": {"effort": "medium"}
  }
  ```

### 3.2 Complete Rendered Prompt Counting

- Rather than naively summing isolated character counts or token counts of separate strings (which ignores Anthropic message framing tokens and turn delimiters), `count_full_request` submits the complete rendered prompt in a single request.
- The request includes: system instructions, user message framing, target source code, static analysis findings, retrieved repository context, and output JSON schema instructions.
- Full request tokens are tracked separately from component tokens (such as `repo_context_tokens`), providing unambiguous telemetry in evaluation runs.

### 3.3 Strict Fallback & Error Policy

- **Approximate Tiktoken Counter**: OpenAI's `tiktoken` BPE is encapsulated in `ApproximateTiktokenCounter`. In accordance with Anthropic guidance, it is explicitly classified as an approximation (`is_heuristic: true`, `method: "approximate_tiktoken_fallback"`). It is forbidden from masquerading as a model-native measurement.
- **Strict Error Handling**: In production execution paths, when the token counting endpoint fails (HTTP 5xx, network timeout, connection refusal), `ApiTokenCounter` strictly raises `TokenCounterError`. It does not silently downgrade to heuristic approximations.
- **Budget Ceiling & Completion Reservation**: In `ConfigBAuditEngine.audit_source()`, budget ceiling checks reserve `max_completion_tokens` (16,384 tokens) alongside the measured rendered input tokens, preventing mid-execution token limit overruns.

---

## 4. Deliverable 3: Backend API, Physical Database, and Webhook Architecture

### 4.1 Endpoint Inventory & Subprocess Persistence

- **API Architecture**: Implemented with FastAPI and structured across 7 functional routers (`audits`, `webhooks`, `runs`, `configurations`, `rules`, `health`, etc.).
- **Physical SQLite Persistence**: Configured with WAL journal mode (`PRAGMA journal_mode=WAL`), foreign key enforcement (`PRAGMA foreign_keys=ON`), and thread-safe connection pooling.
- **Subprocess Restart Proof**: Verified in `test_persistence_across_true_subprocess_restart` (`tests/test_api_physical_db.py`). A standalone Python OS process connected to the SQLite database file, wrote audit records, committed, and exited. The parent test process then connected and verified the persisted data.

### 4.2 Webhook Intake & End-to-End Workflow

The webhook intake path implements the complete 10-step lifecycle:
1. **Raw Body Reception**: Reads raw request bytes before JSON deserialization.
2. **Signature Verification**: Validates `X-Hub-Signature-256` using HMAC-SHA256 over raw request bytes.
3. **Constant-Time Comparison**: Compares signatures using `hmac.compare_digest` to prevent timing attacks.
4. **Event Validation**: Validates `X-GitHub-Event` (`pull_request`) and supported PR actions (`opened`, `synchronize`, `reopened`). Unhandled events return HTTP 202 `ignored` without creating jobs.
5. **Deduplication & Idempotency**: Inspects `X-GitHub-Delivery`. If a delivery ID is already recorded in the database, returns the existing audit ID and acknowledges the duplicate without scheduling additional executions.
6. **Pre-Processing Rejection**: Invalid signatures immediately return HTTP 401 without creating database records or scheduling tasks.
7. **Atomic Persistence**: Persists repository and audit records in SQLite.
8. **Database Failure Protection**: If database persistence fails, the transaction is rolled back, HTTP 500 `DATABASE_PERSISTENCE_ERROR` is returned, and no background task is enqueued.
9. **Single-Job Execution**: Enqueues `execute_background_audit` exactly once via FastAPI background tasks.
10. **Outcome Retrievability**: Audit execution status (`completed`, `failed`), emitted findings, duration, and error messages are fully retrievable via `GET /api/v1/audits/{audit_id}`.

### 4.3 Security Boundaries & Prototype Assumptions

1. **Workspace Path Boundary**:
   - `validate_workspace_path()` restricts audit requests strictly to the current workspace root and explicit paths defined in `AUDITOR_ALLOWED_WORKSPACE_ROOTS`.
   - The shared OS temp directory (`/tmp` or `%TEMP%`) is NOT globally allowed by default, preventing unauthorized scanning of arbitrary temporary host files.
   - Non-existent directories return HTTP 400 `INVALID_WORKSPACE_PATH`; directories outside the allowlist return HTTP 403 `FORBIDDEN_WORKSPACE_PATH`.
2. **Repository & Commit Sanitization**:
   - `validate_repository_and_commit()` enforces alphanumeric regex filtering on repository coordinates and git commit references, blocking command injection and path escaping.
3. **Prototype Execution Limitation**:
   - The current background execution engine relies on FastAPI's in-process `BackgroundTasks`. As documented for thesis evaluation, in-process tasks do not survive unexpected process termination or machine reboots. A durable distributed task queue (e.g. Celery + Redis or RabbitMQ) is recommended for production multi-worker deployment.

---

## 5. Automated Verification Results

All automated test suites, linting checks, and provenance tests passed with zero unexpected failures or regressions across both environments.

### Test Execution Summary

| Command | Exit Code | Observed Result | Scope |
| :--- | :---: | :--- | :--- |
| `uv run ruff check src tests tools` | **0** | `All checks passed!` (0 lint errors) | Static Code Quality |
| `uv run pytest tests/test_benchmark_100_provenance.py` | **0** | `6 passed in 0.41s` | Benchmark Census & Provenance |
| `uv run pytest tests/test_token_counting.py` | **0** | `18 passed in 2.33s` (Private) / `17 passed, 1 skipped` (Public) | Model-Compatible Tokenizer Fidelity |
| `uv run pytest tests/test_api_physical_db.py` | **0** | `8 passed in 2.08s` | Physical DB & Subprocess Restart |
| `uv run pytest tests/test_webhook_intake.py` | **0** | `12 passed in 3.76s` | Webhook Intake, HMAC & Retrievability |
| `uv run pytest tests/` | **0** | `285 passed in 68.38s` (Private) / `284 passed, 1 skipped` (Public) | Full Project Test Suite |
| `uv run pytest data/fixtures/ablation_fixtures_v2/` | **0** | `21 passed in 0.25s` | Context-Ablation V2 Fixtures |

### Test Scope and Environment Reconciliation

1. **Private Canonical Environment**:
   - Total Tests Executed: **306 tests** (285 tests in `tests/` + 21 tests in `data/fixtures/ablation_fixtures_v2/`).
   - Outcome: **306 passed, 0 skipped, 0 failed** in 68.63s.
   - All tests pass including `test_live_gateway_token_counting`, which validates the non-generating gateway token counting contract using local credentials.

2. **Public Staging Environment**:
   - Total Tests Executed: **306 tests** (285 tests in `tests/` + 21 tests in `data/fixtures/ablation_fixtures_v2/`).
   - Outcome: **305 passed, 1 skipped, 0 failed** in 14.88s.
   - Skipped Test: `tests/test_token_counting.py::test_live_gateway_token_counting_without_generation` is explicitly skipped because `.env` and live API credentials are strictly excluded from the public repository to guarantee credential safety.
   - Targeted Week 5–6 Acceptance Suite: Running the 4 core deliverable test files (`test_benchmark_100_provenance.py`, `test_token_counting.py`, `test_api_physical_db.py`, `test_webhook_intake.py`) yields **43 passed, 1 skipped** (out of 44 collected tests).

---

## 6. Safeguards and Baseline Integrity

- **Master Branch**: Unmodified and untouched.
- **Environment Secrets**: `.env` and API credentials remain strictly untracked, unstaged, uncommitted, and unlogged.
- **Historical Evaluation Artifacts**: All frozen historical result records (`config_a_pilot_run.json`, `config_b_pilot_run.json`, `config_c_pilot_run.json`, `config_d_pilot_run.json`) remain untouched in `data/results/`.
- **Inference Cost**: Zero live model generation inference calls were executed during this verification task, incurring **$0.00** in live API spend.
