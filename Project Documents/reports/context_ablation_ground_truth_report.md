# Context-Ablation Ground-Truth Adjudication & Audit Report

**Audit Target:** Repository-Context Ablation Pilot  
**Canonical Run ID:** `ablation-run-1d21ebe5`  
**Base Commit:** `92ecc49` (`feat/context-ablation-pilot`)  
**Audit Branch:** `fix/context-ablation-ground-truth`  
**Evaluated Model Identifier:** `ag/claude-sonnet-4-6`  
**Report Date:** `2026-10-24`  

---

## 1. Executive Summary & Objective

In the repository-context ablation pilot (commit `92ecc49`), two matched arms were evaluated across six multi-file Python micro-repositories:
- **Arm N (No Context):** Target source reviewed in complete isolation.
- **Arm R (Relevant Context):** Identical target source reviewed with mechanically retrieved sibling module definitions.

The raw pilot observed **14 candidate findings** in Arm N and **13 candidate findings** in Arm R, with 5 of 6 fixtures flagged in each arm.

The primary objective of this audit is to:
1. Independently inspect all six micro-repositories at the source level to establish ground-truth security and correctness invariants.
2. Adjudicate all 27 emitted model findings (14 in Arm N, 13 in Arm R) against actual implementation behavior.
3. Determine which fixtures are legitimately clean security controls versus mixed or defective controls.
4. Establish reconciled, eligible clean-control metrics with explicit denominators.
5. Audit smoke-test execution records, request attempts, and cost estimation telemetry.

---

## 2. Canonical Experiment Records & Baseline Verification

A thorough inspection of canonical artifacts was conducted:
- Manifest: `data/ablation_manifest.json`
- Retrieval Index: `data/fixtures/ablation_fixtures/context_retrieval_manifest.json`
- Raw Results: `data/results/context_ablation_pilot/pilot_run/ablation_results.json`
- CSV Summary: `data/results/context_ablation_pilot/pilot_run/ablation_summary.csv`
- Original Report: `Project Documents/reports/context_ablation_pilot_report.md`

### Aggregate Observed Counts Recomputed from Raw JSON:
- Total attempted slots: 12 (6 fixtures $\times$ 2 arms)
- Successful slots (HTTP 200): 12 (100%)
- Total candidate findings emitted: **27**
  - Arm N: **14 candidate findings** across 5 flagged fixtures (1 clean: `ABL-0005`)
  - Arm R: **13 candidate findings** across 5 flagged fixtures (1 clean: `ABL-0003`)

The canonical raw experiment records remain completely unmodified and preserved.

---

## 3. Independent Source-Level Adjudication of All 6 Fixtures

### Fixture ABL-0001 (`repo_01_storage`)
* **Files:** `storage.py`, `validators.py`, `test_storage.py`
* **Intended Security Property:** Prevent directory traversal attacks when saving user uploads.
* **Control Flow & Invariant Inspection:**
  - `storage.py` delegates filename sanitization to `validators.sanitize_filename(raw_filename)`.
  - `validators.py` strictly verifies that:
    1. Input is non-empty (`if not filename: raise ValueError`).
    2. Null bytes are rejected (`if "\x00" in filename: raise ValueError`).
    3. Traversal sequences (`..`), leading slashes, and path separators are stripped via `os.path.basename` and regex stripping (`re.sub(r"\.\.+", "", base).strip(" .")`).
    4. Non-safe characters are replaced with underscores (`re.sub(r"[^a-zA-Z0-9_\-\.]", "_", cleaned)`).
    5. The resulting filename is non-empty (`if not safe_name: raise ValueError`).
  - In `storage.py`, `target_path = (target_dir / clean_name).resolve()`.
  - Directory containment check: `if not str(target_path).startswith(str(target_dir)): raise PermissionError(...)`.
* **Vulnerability Assessment:** Because `clean_name` is guaranteed to contain no path separators (`/`, `\\`) or directory navigation (`..`), `target_path` is strictly a child file directly inside `target_dir`. Path escape is physically impossible.
* **Adjudication Outcome:** **CONFIRMED SAFE** (Confidence: HIGH).
* **Clean Control Status:** **Eligible**.

---

### Fixture ABL-0002 (`repo_02_tenant_doc`)
* **Files:** `documents.py`, `authz.py`, `test_documents.py`
* **Intended Security Property:** Prevent cross-tenant data access (IDOR / multi-tenant isolation).
* **Control Flow & Invariant Inspection:**
  - `documents.py` fetches the document record by `document_id`.
  - If the record does not exist, raises `KeyError`.
  - Guard call:
    ```python
    assert_tenant_boundary(
        user_tenant_id=requesting_tenant_id,
        document_tenant_id=record.get("tenant_id", ""),
    )
    ```
  - In `authz.py`:
    ```python
    if not user_tenant_id or not document_tenant_id:
        raise TenantAccessDenied("Missing required tenant identification context")
    if user_tenant_id != document_tenant_id:
        raise TenantAccessDenied(...)
    ```
* **Evaluation of Model Suspicions:**
  - *Fallback empty string:* If `tenant_id` is missing or empty in the record, `record.get("tenant_id", "")` returns `""`. In `assert_tenant_boundary`, `not document_tenant_id` is `True`, which immediately raises `TenantAccessDenied`. Access is strictly denied, never bypassed.
  - *KeyError on line 34:* Because missing `tenant_id` triggers `TenantAccessDenied` on line 27, line 34 is unreachable if `tenant_id` is absent.
  - *Unused `requesting_user_id`:* The function is specifically a *tenant-level isolation* boundary check. Accepting `requesting_user_id` without using it is an unused argument (ARG001 / maintainability issue), but does not permit unauthorized cross-tenant access.
* **Adjudication Outcome:** **CONFIRMED SAFE** (Confidence: HIGH).
* **Clean Control Status:** **Eligible** (Repaired version `ABL-0002-v2` provided to clarify signature).

---

### Fixture ABL-0003 (`repo_03_query_builder`)
* **Files:** `reports.py`, `schema_whitelist.py`, `test_reports.py`
* **Intended Security Property:** Prevent SQL injection on dynamic table identifiers.
* **Control Flow & Invariant Inspection:**
  - `ALLOWED_METRIC_TABLES` in `schema_whitelist.py` is an immutable `frozenset` containing four static string literals: `"daily_active_users"`, `"monthly_revenue_summary"`, `"audit_trail_events"`, `"system_error_logs"`.
  - `validate_table_whitelist(table_identifier)` normalizes the identifier and verifies `normalized in ALLOWED_METRIC_TABLES`. If not present, raises `ValueError`.
  - The return value is guaranteed to be one of the four static literals.
  - In `reports.py`, `sql = f"SELECT count(*), max(recorded_at) FROM {safe_table} WHERE category = %s"`, with parameter `[metric_category]`.
* **Vulnerability Assessment:** SQL injection is mathematically impossible. The table identifier cannot escape the frozenset whitelist.
* **Adjudication Outcome:** **CONFIRMED SAFE** (Confidence: HIGH).
* **Clean Control Status:** **Eligible**. Landmark case: Arm N raised 2 false alarms; Arm R raised 0.

---

### Fixture ABL-0004 (`repo_04_auth_service`)
* **Files:** `login_handler.py`, `rate_limiter.py`, `test_login.py`
* **Intended Security Property:** Prevent brute-force password guessing via sliding-window rate limiting and constant-time password verification.
* **Control Flow & Invariant Inspection:**
  - `limiter.check_and_record(key=f"auth:{username}")` raises `RateLimitExceeded` if $\ge 5$ attempts occur within 60 seconds.
  - In Python, raising an unhandled exception immediately halts execution; hashing is never reached.
  - Salted hash derived via `hashlib.pbkdf2_hmac("sha256", password, salt, iterations=100_000).hex()`.
  - Constant-time verification: `hmac.compare_digest(derived, stored_hash)`.
* **Evaluation of Model Suspicions:**
  - The model's claim that `check_and_record` does not halt execution was a complete hallucination.
  - The timing difference between rate-limited rejection (fast) and PBKDF2 hashing (slow) is standard rate-limiting architecture designed to prevent CPU exhaustion.
* **Adjudication Outcome:** **CONFIRMED SAFE** (Confidence: HIGH).
* **Clean Control Status:** **Eligible**.

---

### Fixture ABL-0005 (`repo_05_stream_parser`)
* **Files:** `chunk_consumer.py`, `bounded_stream.py`, `test_chunk_consumer.py`
* **Intended Security Property:** Protect against unbounded memory consumption and stream DoS attacks.
* **Control Flow & Invariant Inspection:**
  - `BoundedStreamReader` enforces strict cumulative byte limits (500,000 bytes max) and iteration chunk limits (500 chunks max).
  - When either cap is exceeded, it raises `StreamCapExceeded`.
  - In `chunk_consumer.py`, `process_stream_payload` does not swallow `StreamCapExceeded`; it allows the exception to propagate to the caller.
  - `test_chunk_consumer.py` specifically tests this contract: `with pytest.raises(StreamCapExceeded): process_stream_payload(...)`.
* **Evaluation of Model Suspicions:**
  - Arm R claimed: "StreamCapExceeded is imported at line 6 but never caught... callers will crash unexpectedly."
  - In defensive stream processing, halting execution when an oversized stream is encountered is the intended and correct behavior. Swallowing the exception and returning partial bytes would constitute silent truncation and corruption.
  - Line 6 has an unused import (`from bounded_stream import BoundedStreamReader, StreamCapExceeded`), which is an `F401` code quality issue, but not a security flaw.
* **Adjudication Outcome:** **CONFIRMED SAFE** (Confidence: HIGH).
* **Clean Control Status:** **Eligible** (Repaired version `ABL-0005-v2` removes unused import).

---

### Fixture ABL-0006 (`repo_06_crypto_signer`)
* **Files:** `token_signer.py`, `key_vault.py`, `test_token_signer.py`
* **Intended Security Property:** Generate and verify tamper-proof HMAC-SHA256 session tokens with high-entropy CSPRNG keys.
* **Control Flow & Invariant Inspection:**
  - Key generated via `secrets.token_bytes(32)`.
  - Signed via `hmac.new(key, payload_bytes, hashlib.sha256).hexdigest()`.
  - Constant-time verification via `hmac.compare_digest(signature, expected_sig)`.
* **Vulnerability & Defect Inspection:**
  - *Cryptographic Soundness:* Signature generation and tamper rejection are completely secure.
  - *Defect 1 (Correctness/Robustness):* In `verify_signed_session_token`, `base64.urlsafe_b64decode` is called without exception handling. When supplied with malformed token lengths or padding, it raises an unhandled `binascii.Error` instead of a clean domain `ValueError`.
  - *Defect 2 (Reliability/Availability):* In `EphemeralSigningKeyVault`, keys rotate every 3600 seconds without key versioning (`kid`) or a verification grace period. As soon as rotation occurs, all previously issued valid tokens are rejected with `PermissionError`.
* **Adjudication Outcome:** **MIXED / DEFECTIVE CONTROL** (Confidence: HIGH).
  - Security invariants against token forgery are satisfied.
  - Reliability and exception-handling defects exist.
* **Clean Control Status:** **EXCLUDED from Confirmed-Clean Control Denominator**. (Repaired version `ABL-0006-v2` created with dual-key grace period and robust decoding).

---

## 4. Complete Finding Classification (All 27 Findings)

All 27 findings were adjudicated against six formal categories:
1. Confirmed vulnerability or security defect
2. Confirmed non-security correctness or reliability defect
3. Plausible but unconfirmed concern
4. False positive supported by source-level evidence
5. Duplicate or overlapping finding
6. Not adjudicable from available implementation

| Finding ID | Arm | Fixture | Target File | Line | Adjudication Category | Ground Truth Assessment |
| :--- | :---: | :---: | :--- | :---: | :--- | :--- |
| `ABL-0001-N-1` | N | ABL-0001 | `storage.py` | 21 | **4. False positive** | `clean_name` cannot traverse out; path prefix confusion is impossible. |
| `ABL-0001-N-2` | N | ABL-0001 | `storage.py` | 16 | **4. False positive** | Speculation refuted; `validators.py` guarantees safe, non-empty string. |
| `ABL-0001-R-1` | R | ABL-0001 | `storage.py` | 21 | **4. False positive** | Same as ABL-0001-N-1; path escape is impossible. |
| `ABL-0001-R-2` | R | ABL-0001 | `storage.py` | 16 | **4. False positive** | `validators.py` line 31 explicitly rejects empty sanitized strings. |
| `ABL-0001-R-3` | R | ABL-0001 | `storage.py` | 24 | **3. Plausible concern** | Generic local symlink TOCTOU concern; non-exploitable in standard flow. |
| `ABL-0002-N-1` | N | ABL-0002 | `documents.py` | 12 | **3. Plausible concern** | Unused function parameter in signature (ARG001); tenant check is sound. |
| `ABL-0002-N-2` | N | ABL-0002 | `documents.py` | 27 | **4. False positive** | Empty string raises `TenantAccessDenied` immediately; access is not bypassed. |
| `ABL-0002-N-3` | N | ABL-0002 | `documents.py` | 34 | **4. False positive** | Line 34 is unreachable if `tenant_id` is missing; access denied on line 27. |
| `ABL-0002-R-1` | R | ABL-0002 | `documents.py` | 27 | **4. False positive** | Model admits exception is raised, then alleges ambiguity; no bypass exists. |
| `ABL-0002-R-2` | R | ABL-0002 | `documents.py` | 12 | **3. Plausible concern** | Matches ABL-0002-N-1; code quality issue, not authorization failure. |
| `ABL-0003-N-1` | N | ABL-0003 | `reports.py` | 18 | **4. False positive** | `schema_whitelist.py` strictly restricts return values to 4 static literals. |
| `ABL-0003-N-2` | N | ABL-0003 | `reports.py` | 15 | **4. False positive** | Whitelist raises `ValueError` on bad input; never returns None or empty. |
| `ABL-0004-N-1` | N | ABL-0004 | `login_handler.py` | 24 | **4. False positive** | Hallucination; raising `RateLimitExceeded` halts execution immediately. |
| `ABL-0004-N-2` | N | ABL-0004 | `login_handler.py` | 32 | **4. False positive** | Returning False on mismatched hash formats safely rejects login. |
| `ABL-0004-N-3` | N | ABL-0004 | `login_handler.py` | 13 | **3. Plausible concern** | Multi-megabyte password DoS concern; mitigated per-user by rate limiter. |
| `ABL-0004-R-1` | R | ABL-0004 | `login_handler.py` | 24 | **4. False positive** | Rate-limiting before hashing is standard defense against compute DoS. |
| `ABL-0004-R-2` | R | ABL-0004 | `login_handler.py` | 31 | **3. Plausible concern** | Best-practice hardening debate (100k vs 210k PBKDF2 iterations). |
| `ABL-0004-R-3` | R | ABL-0004 | `login_handler.py` | 34 | **4. False positive** | Safe comparison between hex strings; returns False if mismatched. |
| `ABL-0005-R-1` | R | ABL-0005 | `chunk_consumer.py` | 19 | **3. Plausible concern** | Unhandled exception propagates by design; unused import is a code smell. |
| `ABL-0006-N-1` | N | ABL-0006 | `token_signer.py` | 23 | **4. False positive** | Hallucination; `hmac.new()` has been standard Python since Python 2. |
| `ABL-0006-N-2` | N | ABL-0006 | `token_signer.py` | 34 | **2. Correctness defect** | Malformed base64 input raises unhandled `binascii.Error`. |
| `ABL-0006-N-3` | N | ABL-0006 | `token_signer.py` | 19 | **2. Reliability defect** | Single-key rotation invalidates all active sessions without grace period. |
| `ABL-0006-N-4` | N | ABL-0006 | `token_signer.py` | 32 | **4. False positive** | Hex signature never contains periods; token split is deterministic. |
| `ABL-0006-R-1` | R | ABL-0006 | `token_signer.py` | 23 | **4. False positive** | Hallucination; model admits `hmac.new` is valid, yet emits finding. |
| `ABL-0006-R-2` | R | ABL-0006 | `token_signer.py` | 33 | **2. Reliability defect** | Matches ABL-0006-N-3; active sessions invalidated upon key rotation. |
| `ABL-0006-R-3` | R | ABL-0006 | `token_signer.py` | 34 | **2. Correctness defect** | Matches ABL-0006-N-2; unhandled `binascii.Error` on corrupt input. |
| `ABL-0006-R-4` | R | ABL-0006 | `token_signer.py` | 32 | **4. False positive** | Matches ABL-0006-N-4; benign parsing behavior. |

---

## 5. Recalculated Honest Metrics & Denominator Separation

### A. Full 6-Fixture Cohort (All Observations Included)

| Metric | Arm N (No Context) | Arm R (Relevant Context) | Difference ($\Delta = \text{R} - \text{N}$) |
| :--- | :---: | :---: | :---: |
| Total Evaluated Slots | 6 | 6 | 0 |
| Total Observed Candidate Findings | 14 | 13 | -1 (-7.1%) |
| Confirmed Security Defects | 0 | 0 | 0 |
| Confirmed Correctness/Reliability Defects | 2 | 2 | 0 |
| Supported False Positives | **10** | **7** | **-3 (-30.0%)** |
| Plausible Concerns | 2 | 4 | +2 |
| Fixtures with $\ge 1$ Candidate Finding | 5 / 6 (83.3%) | 5 / 6 (83.3%) | 0.0% |

---

### B. Confirmed Clean-Control Cohort (Verified Denominator = 5 Fixtures)

Excluding `ABL-0006` due to confirmed reliability defects:

| Metric | Arm N (No Context) | Arm R (Relevant Context) | Difference ($\Delta = \text{R} - \text{N}$) |
| :--- | :---: | :---: | :---: |
| **Eligible Clean Controls ($D$)** | **5** (`ABL-0001` to `ABL-0005`) | **5** (`ABL-0001` to `ABL-0005`) | 0 |
| **Observed Findings on Clean Controls** | 10 | 9 | -1 (-10.0%) |
| **Confirmed Security Defects** | 0 | 0 | 0 |
| **Confirmed Correctness Defects** | 0 | 0 | 0 |
| **Supported False Positives** | **8** | **5** | **-3 (-37.5%)** |
| **Plausible Concerns** | 2 | 4 | +2 |
| **Clean Fixtures with $\ge 1$ False Positive** | **4 / 5 (80.0%)** | **3 / 5 (60.0%)** | **-20.0 percentage points** |
| **Clean Fixtures with Zero Findings** | 1 / 5 (`ABL-0005`) | 1 / 5 (`ABL-0003`) | 0 |

### Key Landmark Result on `ABL-0003`:
- In **Arm N**, the model emitted **2 false-positive SQL injection warnings**.
- In **Arm R**, with `schema_whitelist.py` retrieved into the prompt, false positives dropped to **0** (-100% false alarm rate on dynamic identifier queries).

---

## 6. Audit of Smoke-Test Execution and Cost Accounting

- **Smoke-Test Separation:** A smoke test was executed on `ABL-0001` (Run ID: `ablation-run-5cc08b04`, 2026-10-23T17:19:38Z).
- **Independent Execution:** In the full pilot (Run ID: `ablation-run-1d21ebe5`, 2026-10-23T17:24:30Z), `ABL-0001` was re-executed from scratch. Telemetry confirms different prompt tokens (2426 vs 3450) and durations (16.15s vs 19.31s). Smoke responses were **not reused**.
- **Request Attempt Accounting:**
  - Smoke test: 2 requests (1 Arm N + 1 Arm R), 0 retries.
  - Pilot run: 12 requests (6 Arm N + 6 Arm R), 0 retries.
  - Total confirmed live requests: **14 HTTP POST calls** to `/v1/chat/completions`.
- **Cost Estimation Methodology:** Costs were calculated at \$3.00/MTok prompt and \$15.00/MTok completion (standard Sonnet 3.5/4 pricing):
  - Arm N: \$0.1335
  - Arm R: \$0.1415
  - Total pilot cost: \$0.2750 (estimated inference cost, not billed provider invoices).

---

## 7. Versioned Fixture Repairs (v2 Suite)

To address all identified ambiguities and defects without modifying the canonical v1 experiment, repaired fixtures were authored in `data/fixtures/ablation_fixtures_v2/`:
1. `repo_02_tenant_doc_v2`: Removed unused `requesting_user_id` from signature to strictly reflect tenant-isolation scope.
2. `repo_05_stream_parser_v2`: Removed unused `StreamCapExceeded` import and clarified docstring exception contract.
3. `repo_06_crypto_signer_v2`: Added `base64.b64decode(..., validate=True)` with domain `ValueError` handling and implemented multi-key rotation grace periods in `key_vault.py`.

All 9 v2 unit tests pass (`uv run pytest data/fixtures/ablation_fixtures_v2`).

---

## 8. Scientific Conclusions

1. **Observed Facts:**
   - Raw candidate findings: 14 (Arm N) vs 13 (Arm R).
   - On the 5 confirmed-clean controls, false positives dropped from 8 down to 5 (-37.5%).
   - On `ABL-0003`, providing the whitelist module eliminated 2 false-positive SQL injection alarms (100% reduction).
2. **Supported Interpretation:**
   - LLMs evaluate single-file security checks with defensive skepticism. Providing verified cross-file context grounds the model in actual guarantees and measurably suppresses false alarms on sound code.
3. **Unresolved Hypotheses:**
   - Generalization across deep transitive call graphs ($N > 2$ modules) requires further experimentation.
   - Run-to-run stochastic variance requires multi-trial replicates ($N \ge 3$).
4. **Invalid Conclusions:**
   - It cannot be concluded that repository context eliminates all false alarms (Arm R still produced 5 false positives across 3 clean fixtures).
   - Findings cannot be automatically treated as false positives without inspecting source-level implementations.
