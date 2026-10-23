# Corrected Pilot Analysis: Repository-Context Ablation

**Document Type:** Reconciled & Adjudicated Benchmark Report  
**Pilot Run ID:** `ablation-run-1d21ebe5`  
**Execution Timestamp:** `2026-10-23T17:24:30.487581+00:00`  
**Adjudication Release:** `2026-10-24`  
**Audit Branch:** `fix/context-ablation-ground-truth`  
**Target Architecture:** Arm N (Isolated Prompt) vs Arm R (Context-Enriched Prompt)  

---

## 1. Executive Summary

This report corrects and supersedes the initial raw findings report for the **Repository-Context Ablation Pilot**. While the initial report accurately recorded the raw model candidate outputs (14 in Arm N, 13 in Arm R), this corrected analysis incorporates independent source-code adjudication to distinguish confirmed defects, plausible concerns, and proven false positives.

Furthermore, this report establishes a defensible clean-control denominator by excluding `ABL-0006` due to confirmed reliability defects in key rotation and error decoding, evaluating clean-control accuracy on a **5-fixture confirmed-clean baseline**.

---

## 2. Reconciled Metrics: Observed vs Adjudicated

### Table 1: Raw Observed vs Adjudicated Metrics across All 6 Fixtures

| Metric Category | Arm N (No Context) | Arm R (Relevant Context) | Delta ($\Delta = \text{R} - \text{N}$) |
| :--- | :---: | :---: | :---: |
| **Observed Candidate Findings** | **14** | **13** | **-1 (-7.1%)** |
| Confirmed Security Defects | 0 | 0 | 0 |
| Confirmed Correctness / Reliability Defects | 2 | 2 | 0 |
| Plausible Concerns | 2 | 4 | +2 |
| **Supported False Positives** | **10** | **7** | **-3 (-30.0%)** |
| Fixtures Flagged ($\ge 1$ Candidate Finding) | 5 / 6 (83.3%) | 5 / 6 (83.3%) | 0.0% |

---

### Table 2: Eligible Clean-Control Metrics (Confirmed-Clean Denominator = 5 Fixtures)

Excluding `ABL-0006` from the clean baseline due to unhandled `binascii.Error` and lack of session rotation tolerance:

| Metric Category | Arm N (No Context) | Arm R (Relevant Context) | Delta ($\Delta = \text{R} - \text{N}$) |
| :--- | :---: | :---: | :---: |
| **Eligible Clean Fixtures ($D$)** | **5** (`ABL-0001` to `ABL-0005`) | **5** (`ABL-0001` to `ABL-0005`) | 0 |
| **Candidate Findings on Clean Fixtures** | 10 | 9 | -1 (-10.0%) |
| Confirmed Security Defects | 0 | 0 | 0 |
| Confirmed Correctness Defects | 0 | 0 | 0 |
| **Supported False Positives** | **8** | **5** | **-3 (-37.5%)** |
| Plausible Concerns | 2 | 4 | +2 |
| **Clean Fixtures Flagged with False Positives** | **4 / 5 (80.0%)** | **3 / 5 (60.0%)** | **-20.0%** |
| Clean Fixtures with Zero Findings | 1 / 5 (`ABL-0005`) | 1 / 5 (`ABL-0003`) | 0 |

---

## 3. Case-by-Case Adjudication Summary

### `ABL-0001` (Path Traversal Sanitization — `storage.py` + `validators.py`)
- **Arm N:** 2 candidate findings (Path traversal prefix check, blind trust in external sanitizer).
- **Arm R:** 3 candidate findings (Prefix confusion, whitespace filename, TOCTOU).
- **Adjudication:** `validators.py` strictly neutralizes path traversal characters. All traversal and empty-string findings are **False Positives**. TOCTOU is classified as a low-probability plausible concern.
- **Fixture Status:** **Confirmed Safe**.

### `ABL-0002` (Multi-Tenant IDOR Protection — `documents.py` + `authz.py`)
- **Arm N:** 3 candidate findings (User identity ignored, empty tenant fallback, KeyError).
- **Arm R:** 2 candidate findings (Tenant boundary bypassed on missing tenant_id, user identity ignored).
- **Adjudication:** Empty tenant IDs trigger immediate `TenantAccessDenied`. The claim that missing tenant IDs allow access is a **False Positive**. KeyError is a **False Positive** (unreachable). The unused `requesting_user_id` parameter is classified as a **Plausible Concern** (code quality / unused argument).
- **Fixture Status:** **Confirmed Safe**.

### `ABL-0003` (Dynamic SQL Identifier Whitelisting — `reports.py` + `schema_whitelist.py`)
- **Arm N:** 2 candidate findings (SQL injection via unverified whitelist return, No null guard).
- **Arm R:** **0 candidate findings**.
- **Adjudication:** Whitelist restricts return values to 4 static literals; SQL injection is impossible. Arm N findings are **False Positives**. Providing repository context **completely suppressed both false alarms** (100% reduction).
- **Fixture Status:** **Confirmed Safe**.

### `ABL-0004` (Brute-Force Rate Limiting — `login_handler.py` + `rate_limiter.py`)
- **Arm N:** 3 candidate findings (Rate limit does not halt execution, PBKDF2 hex mismatch, password length DoS).
- **Arm R:** 3 candidate findings (Timing enumeration, 100k iteration adequacy, hex string compare).
- **Adjudication:** `RateLimitExceeded` halts execution immediately (Arm N finding 1 is a hallucination). Digest comparison is safe. PBKDF2 iteration depth is a plausible hardening suggestion.
- **Fixture Status:** **Confirmed Safe**.

### `ABL-0005` (Bounded Stream Memory Protection — `chunk_consumer.py` + `bounded_stream.py`)
- **Arm N:** 0 candidate findings.
- **Arm R:** 1 candidate finding (StreamCapExceeded exception never caught).
- **Adjudication:** Propagating `StreamCapExceeded` halts oversized payload processing by design, verified by unit tests. The unused import in `chunk_consumer.py` is a code smell. Not a security vulnerability.
- **Fixture Status:** **Confirmed Safe**.

### `ABL-0006` (CSPRNG Token Signing — `token_signer.py` + `key_vault.py`)
- **Arm N:** 4 candidate findings (`hmac.new` does not exist, base64 padding crash, key rotation invalidation, multi-dot split).
- **Arm R:** 4 candidate findings (`hmac.new` does not exist, key rotation invalidation, base64 padding crash, multi-dot split).
- **Adjudication:** `hmac.new` claims are hallucinations (**False Positives**). Unhandled `binascii.Error` on corrupt base64 and lack of session rotation tolerance are **Confirmed Reliability Defects**.
- **Fixture Status:** **Mixed / Defective Control** (Excluded from clean denominator).

---

## 4. Methodological Audit & Scientific Categorization

1. **Observed Facts:**
   - Raw candidate alerts: 14 (Arm N) vs 13 (Arm R).
   - Confirmed security defects: 0 in both arms.
   - Ground-truth false positives on clean fixtures: 8 (Arm N) vs 5 (Arm R), a net reduction of **3 false positives (-37.5%)**.
   - Landmark suppression on `ABL-0003`: 2 false alarms reduced to 0.
2. **Supported Interpretations:**
   - Single-file prompt framing forces LLMs to make pessimistic assumptions about external functions. Mechanically providing relevant definitions grounds model reasoning and prevents false alarms.
3. **Unresolved Hypotheses:**
   - Whether this precision advantage scales to deep multi-hop call graphs without inducing prompt confusion.
   - Stochastic variability across repeated runs ($N \ge 3$).
4. **Invalid Conclusions:**
   - Context does not magically eliminate all false positives (3 of 5 clean fixtures still triggered warnings in Arm R).
   - Raw candidate alert counts cannot be cited as false-positive counts without source-level adjudication.
