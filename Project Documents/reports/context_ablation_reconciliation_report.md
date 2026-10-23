# Context-Ablation Finding Ledger & Clean-Control Eligibility Reconciliation Report

**Audit Target:** Canonical Finding Ledger, Password Security Ground Truth & Methodological Interpretation  
**Run ID:** `ablation-run-1d21ebe5`  
**Base Commit:** `ba18556` (`fix(evaluation): verify salt handling and tier definitions`)  
**Audit Branch:** `fix/context-ablation-final-integrity`  
**Evaluated Model Identifier:** `ag/claude-sonnet-4-6`  
**Report Date:** `2026-10-24`  

---

## 1. Executive Summary & Audit Purpose

This reconciliation audit finalizes the accounting, ledger consistency, standards alignment, and clean-control eligibility framework following the repository-context ablation pilot.

Specifically, this report establishes:
1. **A deterministic, one-to-one finding ledger** mapping every raw model output item from `pilot_run/ablation_results.json` directly to an adjudication record with a stable identity `(run_id, fixture_id, arm, raw_finding_index)` (27/27 findings accounted for).
2. **Complete mathematical reconciliation of `ABL-0006`:** detailing all 4 findings in Arm N and all 4 in Arm R, explaining the exact subtraction arithmetic that reconciles all-fixture candidate findings (14 in Arm N, 13 in Arm R) and false positives (10 in Arm N, 7 in Arm R) with the clean cohorts.
3. **Rigorous Reassessment of `ABL-0004` (Password Security, Salt Handling & Work Factor):**
   - Qualified citations of **NIST SP 800-63B Revision 4** (superseding Revision 3) and the **OWASP Password Storage Cheat Sheet** (distinguishing online brute-force defense from offline GPU cracking, and qualifying the 600,000-iteration PBKDF2 recommendation for FIPS-140 compliance).
   - Source-level audit of salt handling in `ABL-0004-v1` (unverified caller-provided salt, missing length/entropy checks, and absent metadata storage) vs `ABL-0004-v2` (CSPRNG salt generation, $\ge 32$-bit entropy validation, structured credential record creation, and dynamic parameter verification).
   - Transparent benchmarking provenance: explicitly distinguishing historical inline measurements from the reproducible versioned benchmark (`tools/benchmark_pbkdf2_payloads.py` and `pbkdf2_benchmark_measurements.json`), and defining the strict technical boundary of what in-process cryptographic benchmarking measures.
4. **Three Unambiguous Clean-Control Cohort Tiers:**
   - **Tier 1: Operational Online-Authentication Cohort ($D = 5$)** (`ABL-0001` through `ABL-0005`)
   - **Tier 2: Comprehensive Security-Clean Cohort ($D = 4$)** (`ABL-0001`, `ABL-0002`, `ABL-0003`, `ABL-0005`)
   - **Tier 3: Lint-Clean / Zero-Code-Smell Cohort ($D = 1$)** (`ABL-0003` only)
5. **Rigorous Statistical & Methodological Interpretation:**
   - Explicit qualification that Tiers 1, 2, and 3 are **overlapping, post-hoc exploratory sensitivity subsets** of the same six fixture pairs evaluated in a single run.
   - Refutation of claims of independent replication or formal statistical significance across tiers: the preservation of $\Delta = -3$ across Tiers 1 and 2 is an **arithmetic consequence of subset subtraction** (since `ABL-0004` emitted 2 false positives in each arm, $\Delta = 2 - 2 = 0$).
   - Explicit framing of Tier 3 as a **single matched illustrative case** (`ABL-0003`), rather than cohort-level evidence of general efficacy.

---

## 2. One-to-One Canonical Finding Ledger

The canonical finding ledger is maintained in machine-readable JSON ([`data/ablation_canonical_ledger.json`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/data/ablation_canonical_ledger.json)) and tabular CSV ([`data/results/context_ablation_pilot/canonical_finding_ledger.csv`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/data/results/context_ablation_pilot/canonical_finding_ledger.csv)).

### Strict Verification Invariants Satisfied:
- **Total Raw Output Findings:** Exactly **27** (Arm N: 14, Arm R: 13).
- **Total Ledger Entries:** Exactly **27** (100% one-to-one mapping; 0 missing, 0 fabricated).
- **Stable Identifiers:** Each finding possesses a deterministic ID: `ABL-XXXX-{N|R}-Y` (where Y is 1-indexed record position).
- **Exclusivity:** Every finding has exactly one primary classification. Category sums match arm sums identically:
  - Arm N: $0 \text{ (Vuln)} + 2 \text{ (Defect)} + 2 \text{ (Concern)} + 10 \text{ (FP)} = 14$
  - Arm R: $0 \text{ (Vuln)} + 2 \text{ (Defect)} + 4 \text{ (Concern)} + 7 \text{ (FP)} = 13$
- **Peer Matching:** Cross-arm matching (`peer_match_id`) is tracked as an orthogonal relational attribute; matching two findings does not collapse or remove either record.

---

## 3. Complete Accounting and Reconciliation of `ABL-0006`

In earlier draft reports, confusion arose because excluding `ABL-0006` reduced supported false positives by 2 in each arm ($10 \rightarrow 8$ in Arm N, and $7 \rightarrow 5$ in Arm R), while discussion focused solely on one HMAC existence hallucination.

Here is the complete, itemized audit of all 8 findings emitted for `ABL-0006`:

### Arm N Records for `ABL-0006` (4 Findings Total):
1. **`ABL-0006-N-1`** — *Title: Use of non-existent `hmac.new()`*
   - **Primary Category:** `4_supported_false_positive`
   - **Evidence:** Model hallucinated that `hmac.new()` does not exist in Python 3. `hmac.new()` has been standard since Python 2/3.
2. **`ABL-0006-N-2`** — *Title: Missing padding validation on base64 token segment before decoding*
   - **Primary Category:** `2_confirmed_correctness_or_reliability_defect`
   - **Evidence:** `base64.urlsafe_b64decode` without proper padding or with malformed length raises unhandled `binascii.Error`, crashing the server on malformed input.
3. **`ABL-0006-N-3`** — *Title: No key versioning — key rotation invalidates all existing valid tokens silently*
   - **Primary Category:** `2_confirmed_correctness_or_reliability_defect`
   - **Evidence:** `EphemeralSigningKeyVault` maintains only a single active key rotated every 3600s. Key rotation immediately causes `PermissionError` on all previously issued active tokens.
4. **`ABL-0006-N-4`** — *Title: Token with multiple '.' separators parsed incorrectly*
   - **Primary Category:** `4_supported_false_positive`
   - **Evidence:** Token split uses `token.split('.', 1)`. The signature is generated via `hexdigest()`, which consists strictly of hexadecimal characters `[0-9a-f]` and never contains periods. Token splitting is completely deterministic and safe.

### Arm R Records for `ABL-0006` (4 Findings Total):
1. **`ABL-0006-R-1`** — *Title: Use of non-existent `hmac.new`*
   - **Primary Category:** `4_supported_false_positive`
   - **Evidence:** Counterpart to `N-1`. The model explicitly self-debates in its description and admits `hmac.new` is valid in Python 3, yet still emits the finding.
2. **`ABL-0006-R-2`** — *Title: Key rotation between token issuance and verification breaks signature validation*
   - **Primary Category:** `2_confirmed_correctness_or_reliability_defect`
   - **Evidence:** Counterpart to `N-3`. Verified single-key rotation causes session invalidation.
3. **`ABL-0006-R-3`** — *Title: Missing padding handling in base64 URL-safe decode may raise `binascii.Error`*
   - **Primary Category:** `2_confirmed_correctness_or_reliability_defect`
   - **Evidence:** Counterpart to `N-2`. Unhandled `binascii.Error` on malformed base64 input.
4. **`ABL-0006-R-4`** — *Title: Token split on first `.` only — multi-dot payloads parsed incorrectly*
   - **Primary Category:** `4_supported_false_positive`
   - **Evidence:** Counterpart to `N-4`. `hexdigest()` signature never contains dots; split is safe.

### Subtraction Arithmetic Reconciliation:
When `ABL-0006` is excluded:
- **Arm N Excluded:** 2 Defects (`N-2`, `N-3`) + 2 False Positives (`N-1`, `N-4`) = 4 findings.
  - Arm N False Positives: $10 - 2 = \mathbf{8}$.
  - Arm N Total Findings: $14 - 4 = \mathbf{10}$.
- **Arm R Excluded:** 2 Defects (`R-2`, `R-3`) + 2 False Positives (`R-1`, `R-4`) = 4 findings.
  - Arm R False Positives: $7 - 2 = \mathbf{5}$.
  - Arm R Total Findings: $13 - 4 = \mathbf{9}$.

The subtraction arithmetic is exact across all categories.

---

## 4. Deep Reassessment of `ABL-0004` (Password Security, Salt Handling & Work Factor)

### A. Source-Level Salt Handling Audit (`ABL-0004-v1`)
In `ABL-0004-v1` ([`data/fixtures/ablation_fixtures/repo_04_auth_service/login_handler.py`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/data/fixtures/ablation_fixtures/repo_04_auth_service/login_handler.py)):
- Function `process_login_attempt(username, password_attempt, stored_hash, salt, limiter)` accepts `salt: str` directly from the caller.
- **Unverified Salt Generation:** The module contains no salt generation function; unit test `test_login.py` passes a static dummy string `"random_salt"`.
- **Unverified Salt Entropy & Length:** No minimum length or entropy checks are performed on `salt` before passing to `hashlib.pbkdf2_hmac`.
- **Absent Metadata Storage:** The module does not store or manage credentials; salt and scheme/cost metadata persistence is unaddressed.
- **Threat Model Limits:**
  - Rate limiting is keyed solely to `f"auth:{username}"`. An attacker distributing attempts across multiple distinct usernames (credential stuffing / password spraying) will not trigger the rate limit.
  - The module imposes no length ceiling on `password_attempt`.
  - While sliding-window rate limiting halts repeated attempts against a single known username, it does not provide comprehensive password-storage security.
- **Ground-Truth Classification:** Under comprehensive security evaluation, `ABL-0004-v1` is classified as **`UNRESOLVED_SECURITY_CONCERN`**. It is included only under a narrow operational single-account online threat model (Tier 1).

---

### B. Qualification of Authoritative Guidance (NIST & OWASP)

1. **NIST SP 800-63B Revision 4 (Section 3.1.1.2 Memorized Secret Verifiers):**
   - *Supersedes Revision 3* (which specified a minimum floor of 10,000 iterations for PBKDF2).
   - Revision 4 mandates:
     - Passwords *SHALL* be salted and hashed using an approved scheme (e.g., SP 800-132 / PBKDF2).
     - Salts *SHALL* be at least 32 bits (4 bytes) in length and chosen to minimize collisions.
     - Both salt value and resulting hash *SHALL* be stored alongside scheme and cost-factor metadata to support future migration.
     - Cost factors *SHOULD* be set as high as practical without harming verifier performance.
2. **OWASP Password Storage Cheat Sheet:**
   - Prioritizes memory-hard functions (Argon2id primary recommendation, followed by scrypt and bcrypt work factor 10–12).
   - Recommends PBKDF2 with HMAC-SHA256 at **600,000 iterations or more** *when FIPS-140 compliance is required*. This is a specific compliance recommendation rather than a universal requirement for all applications.
3. **Distinct Threat Models:**
   - **Online Brute Force / Credential Stuffing:** Defended primarily via sliding-window rate limiting (5 requests/60s). Because the rate limiter halts requests before hashing, 100,000 iterations provides effective defense against single-account online guessing.
   - **Offline Hash Cracking:** In the event of a database compromise, 100,000 iterations offers lower resistance against GPU clusters than 600,000 iterations.

---

### C. Empirical Cryptographic & Payload-Size Benchmarking

#### 1. Methodological Provenance & Technical Scope:
- **Historical Measurements Note:** The timing values in earlier draft reports were generated via an ad-hoc inline command during an interactive shell session; their raw timing vectors and machine telemetry were not saved in a versioned repository artifact.
- **Auditable Benchmark Implementation:** To establish verifiable provenance without inventing historical logs, a standalone microbenchmark was committed to [`tools/benchmark_pbkdf2_payloads.py`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/tools/benchmark_pbkdf2_payloads.py). Its raw timing vectors and platform metadata are versioned in [`data/results/context_ablation_pilot/pbkdf2_benchmark_measurements.json`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/data/results/context_ablation_pilot/pbkdf2_benchmark_measurements.json).
- **Strict Scope of Measurement:** The benchmark measures in-process execution of string UTF-8 encoding and `hashlib.pbkdf2_hmac` in memory using `time.perf_counter()`.
- **What Is NOT Measured:** It does **not** measure HTTP request body streaming, ASGI/WSGI parsing, framework payload caps, network buffering, or concurrent request thread exhaustion.

#### 2. Reproducible Benchmark Results (10 Repetitions, 1 Warmup Run):

| Configuration | Payload Size | Iteration Count | Mean Time | Std Dev ($\sigma$) | Min / Max | Technical Analysis |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| Typical Secret | 12 bytes | 100,000 | **25.57 ms** | $\pm 0.64\text{ ms}$ | 25.24 / 27.39 ms | Baseline single-secret authentication |
| Large Secret | 1 Megabyte | 100,000 | **26.61 ms** | $\pm 0.31\text{ ms}$ | 26.27 / 27.20 ms | +1.04 ms (+4.1%) overhead |
| Extreme Secret | 10 Megabytes | 100,000 | **33.04 ms** | $\pm 0.54\text{ ms}$ | 31.97 / 33.85 ms | +7.47 ms (+29.2%) total overhead |
| Hardened (OWASP) | 12 bytes | 600,000 | **152.23 ms** | $\pm 1.07\text{ ms}$ | 150.57 / 153.97 ms | $6\times$ server compute load |

#### 3. Cryptographic Mechanism (RFC 2104 / FIPS 198-1):
$$\text{If } \operatorname{len}(K) > B \text{ (where } B = 64 \text{ bytes for SHA-256), } K' = \operatorname{SHA-256}(K)$$
When `password_attempt` exceeds 64 bytes, HMAC hashes the entire payload with SHA-256 **once** down to a 32-byte key $K'$. Hashing 10 MB with SHA-256 takes ~7 ms in C/OpenSSL. **All subsequent 100,000 PBKDF2 iterations operate strictly on the 32-byte key $K'$.** PBKDF2 does *not* re-hash 10 MB on every iteration.

However, unbounded memory allocation for user payloads remains a valid defensive hardening concern.

---

### D. Hardened Replacement Fixture: `ABL-0004-v2`

To address salt handling, work factor, and input bounds without mutating canonical v1 experiment artifacts, `ABL-0004-v2` was implemented in [`data/fixtures/ablation_fixtures_v2/repo_04_auth_service_v2/`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/data/fixtures/ablation_fixtures_v2/repo_04_auth_service_v2):
1. **Cryptographically Secure Salt Generation:**
   ```python
   def generate_salt(num_bytes: int = 16) -> str:
       if not isinstance(num_bytes, int) or num_bytes < 4:
           raise ValueError("Salt size must be an integer of at least 4 bytes (32 bits) per NIST SP 800-63B Rev 4")
       return secrets.token_hex(num_bytes)
   ```
   Uses CSPRNG (`secrets.token_hex`), returning $2 \times \text{num\_bytes}$ hex characters. A 16-byte salt provides 128 bits of entropy.
   *Collision Risk Discussion:* By the birthday bound, an expected collision requires $\approx 2^{64}$ generated salts. While random generation cannot provide mathematical impossibility of collision, a 128-bit CSPRNG salt makes accidental collision astronomically improbable in any realistic password store.
2. **Strict Hexadecimal Salt Validation:**
   `validate_salt(salt)` rejects non-string values, empty strings, strings shorter than 8 hex characters, odd-length strings, and non-hexadecimal characters (`[0-9a-fA-F]`).
3. **Safe Default Record Creation:**
   `create_credential_record(password, *, num_salt_bytes=16, iterations=600_000)` **always** generates a fresh random salt. Callers cannot pass predictable or static salts through this interface.
4. **Explicit Legacy Import Contract:**
   `import_legacy_credential_record(password, salt, *, iterations=600_000)` is provided for credential migration, accompanied by an explicit contract requiring the caller to guarantee CSPRNG generation, uniqueness, and persistence.
5. **Dynamic Record Verification:**
   `verify_credential_record(record, password_attempt, limiter, username=None)` extracts and uses the salt, scheme, and iteration count recorded in `record`, rather than silently relying on changing module defaults.
6. **Future Migration Support:**
   `check_needs_rehash(record, target_scheme, target_iterations)` detects outdated parameters for safe gradual upgrades.
7. **Full Test Suite:** 12 unit tests in `test_login_v2.py` verify all features, salt entropy controls, and edge cases (all 12 pass).

---

## 5. Multi-Tier Clean-Control Eligibility Framework

To provide complete scientific neutrality, three distinct tiers are formally defined:

### Tier 1: Operational Online-Authentication Cohort ($D = 5$)
- **Fixtures:** `ABL-0001`, `ABL-0002`, `ABL-0003`, `ABL-0004`, `ABL-0005`.
- **Inclusion Predicate:** Fixtures with zero confirmed security vulnerabilities under a narrow single-target online authentication threat model.
- **Rationale for `ABL-0004`:** Sliding-window rate limiting on `auth:{username}` halts brute-force guessing against a known account; constant-time comparison prevents timing enumeration.
- **Explicit Excluded Threats:** Does not protect against distributed credential stuffing / password spraying across multiple usernames; does not protect against offline cracking if hashes are stolen; does not validate salt generation, uniqueness, or persistence contracts; does not bound memory allocation for oversized payloads.

### Tier 2: Comprehensive Security-Clean Cohort ($D = 4$)
- **Fixtures:** `ABL-0001`, `ABL-0002`, `ABL-0003`, `ABL-0005`.
- **Inclusion Predicate:** Fixtures whose security-relevant properties within their local modules are completely verified, with no unmitigated security concerns and no reliance on unstated caller contracts for core cryptographic properties.
- **Exclusions:**
  - `ABL-0006`: `MIXED_OR_DEFECTIVE` (confirmed reliability defects: unhandled exception crash and session invalidation).
  - `ABL-0004`: `UNRESOLVED_SECURITY_CONCERN` (unverified caller-provided salt, 100k < 600k iterations, unvalidated input bounds).

### Tier 3: Lint-Clean / Zero-Code-Smell Cohort ($D = 1$)
- **Fixtures:** `ABL-0003` only.
- **Inclusion Predicate:** Zero code smells, zero linter warnings (Ruff clean), and strict canonical boundaries.
- **Exclusions:**
  - `ABL-0001`: Fragile `startswith` directory check instead of `Path.is_relative_to()`.
  - `ABL-0002`: Unused function parameter `requesting_user_id` (Ruff `ARG001`).
  - `ABL-0004`: Unverified salt contract, 100k iterations, unvalidated input length.
  - `ABL-0005`: Unused import `StreamCapExceeded` in consumer (Ruff `F401`).
  - `ABL-0006`: Confirmed reliability defects (unhandled `binascii.Error`, key rotation drop).
- **Methodological Qualification:** This represents a single matched illustrative case (`ABL-0003`), NOT a cohort-level statistical proof of general efficacy.

---

## 6. Reconciled Metrics Across All Three Clean-Cohort Tiers

### Table 1: All 6 Micro-Repositories (Descriptive Cohort, Denominator = 6)

| Fixture ID | Micro-Repository | Arm N Total | Arm N FPs | Arm N Defects | Arm N Concerns | Arm R Total | Arm R FPs | Arm R Defects | Arm R Concerns | Context Effect Observed |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `ABL-0001` | `repo_01_storage` | 2 | 2 | 0 | 0 | 3 | 2 | 0 | 1 | Traversal critiques shifted |
| `ABL-0002` | `repo_02_tenant_doc` | 3 | 2 | 0 | 1 | 2 | 1 | 0 | 1 | Suppressed false KeyError |
| `ABL-0003` | `repo_03_query_builder` | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | **Suppressed 2 SQL Injection FPs** |
| `ABL-0004` | `repo_04_auth_service` | 3 | 2 | 0 | 1 | 3 | 2 | 0 | 1 | Hardening analysis retained |
| `ABL-0005` | `repo_05_stream_parser` | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | Unhandled exception identified |
| `ABL-0006` | `repo_06_crypto_signer` | 4 | 2 | 2 | 0 | 4 | 2 | 2 | 0 | Excluded mixed control |
| **Total** | | **14** | **10** | **2** | **2** | **13** | **7** | **2** | **4** | **Net: -3 False Positives** |

---

### Table 2: Comparative Metrics Across Clean-Control Tiers

| Metric Category | Tier 1: Operational ($D = 5$) | Tier 1: Operational ($D = 5$) | Tier 1 Delta | Tier 2: Comprehensive ($D = 4$) | Tier 2: Comprehensive ($D = 4$) | Tier 2 Delta | Tier 3: Zero Smell ($D = 1$) | Tier 3: Zero Smell ($D = 1$) | Tier 3 Delta |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| | **Arm N** | **Arm R** | **$\Delta$** | **Arm N** | **Arm R** | **$\Delta$** | **Arm N** | **Arm R** | **$\Delta$** |
| **Eligible Clean Controls ($D$)** | **5** | **5** | **0** | **4** | **4** | **0** | **1** | **1** | **0** |
| **Total Candidate Findings** | 10 | 9 | -1 (-10.0%) | 7 | 6 | -1 (-14.3%) | 2 | 0 | -2 (-100%) |
| Confirmed Security Defects | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Confirmed Reliability Defects | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Supported False Positives** | **8** | **5** | **-3 (-37.5%)** | **6** | **3** | **-3 (-50.0%)** | **2** | **0** | **-2 (-100%)** |
| Plausible Concerns | 2 | 4 | +2 | 1 | 3 | +2 | 0 | 0 | 0 |
| **Clean Fixtures Flagged ($\ge 1$ FP)** | **4 / 5 (80%)** | **3 / 5 (60%)** | **-20.0%** | **3 / 4 (75%)** | **2 / 4 (50%)** | **-25.0%** | **1 / 1 (100%)** | **0 / 1 (0%)** | **-100.0%** |

---

### 7. Methodological Interpretation: Overlapping Tiers & Statistical Limits

1. **Non-Independent Sensitivity Subsets:**
   Tiers 1, 2, and 3 are **not** independent experimental replications. They are nested, post-hoc sensitivity analyses evaluated over subsets of the same six fixture pairs from a single evaluation run.
2. **Arithmetic Origin of the Invariant $\Delta = -3$:**
   The observation that $\Delta_{\text{FPs}} = -3$ is identical in Tier 1 ($D=5$) and Tier 2 ($D=4$) is an **arithmetic artifact of subset subtraction**, not independent confirmation of robustness. Specifically:
   - On `ABL-0004`, Arm N emitted 2 false positives (`N-1`, `N-2`).
   - On `ABL-0004`, Arm R emitted 2 false positives (`R-1`, `R-3`).
   - The within-fixture difference for `ABL-0004` is $2 - 2 = 0$.
   - Subtracting equal numbers of false positives from both arms mathematically guarantees that the net difference remains unchanged: $(8 - 2) - (5 - 2) = 6 - 3 = 3$.
3. **Single Case Characterization for Tier 3:**
   Tier 3 contains solely `ABL-0003`. The reduction of false positives from 2 to 0 on `ABL-0003` must be interpreted as a **single matched illustrative case** demonstrating that dynamic SQL table whitelisting context can clarify an otherwise ambiguous query construction pattern. It cannot be cited as a cohort-level statistical validation.
4. **Absence of Stochastic Variation Estimates:**
   The experiment was conducted as a single pilot run per arm ($N=1$ per arm per fixture). It does not estimate run-to-run stochastic variance, model temperature drift, or non-deterministic sampling variance.
5. **No Claim of General Statistical Significance:**
   These findings demonstrate a consistent descriptive direction across these overlapping subsets on the evaluated pilot fixtures. They do not constitute formal statistical hypothesis testing and cannot be generalized uncritically to production codebases.

---

## 8. Versioning, Artifacts, and Safety Verification

- **Original v1 Artifacts Preserved (Strictly Immutable):**
  - `data/fixtures/ablation_fixtures/` (unchanged)
  - `data/results/context_ablation_pilot/pilot_run/ablation_results.json` (unchanged)
- **Reconciled Governance Artifacts:**
  - `data/ablation_canonical_ledger.json` (machine-readable finding ledger)
  - `data/results/context_ablation_pilot/canonical_finding_ledger.csv` (tabular finding ledger)
  - `data/results/context_ablation_pilot/ledger_metrics_summary.json` (3-tier summary metrics with methodological interpretation)
  - `data/ablation_adjudication_manifest.json` (schema v1.2.0 with tier eligibility and excluded threat descriptions)
  - `data/results/context_ablation_pilot/pbkdf2_benchmark_measurements.json` (versioned 10-repetition benchmark provenance data)
  - `tools/benchmark_pbkdf2_payloads.py` (reproducible benchmark tool)
  - `tests/test_context_ablation_reconciliation.py` (regression tests covering all 3 tiers and non-independent labeling)
  - `tests/test_context_ablation_adjudication.py` (manifest and denominator schema tests)
- **Repaired v2 Fixture Suite:**
  - `data/fixtures/ablation_fixtures_v2/` (21 unit tests pass across `repo_02_v2`, `repo_04_v2`, `repo_05_v2`, `repo_06_v2`)
