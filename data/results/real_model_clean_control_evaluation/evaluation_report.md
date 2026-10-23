# AI Code Auditor — Experimental Evaluation & Provenance Integrity Report

**Generated:** `2026-10-23T16:43:10.029994+00:00`  
**Execution Mode:** `live`  
**Git Commit Baseline:** `current-head`  
**Evaluation Matching Tolerance:** `+-10 lines (ADR-10 locked methodology)`  

---

## 1. Provenance Audit & Scientific Validity Clarifications

### Origin of Benchmark Numbers & Gateway Metadata:
- **Config A (Deterministic Static Analysis):** Ruff 0.16.10 + Semgrep CE 1.180.0. 100% reproducible locally without network or API dependencies.
- **Config B (LLM Only):** Historical pilot run executed on 2026-10-09 against gateway identifier `ag/claude-sonnet-4-6`. 18/18 defective cases completed successfully.
- **Config C (Static + LLM Triage):** Historical pilot run executed on 2026-10-10 against gateway identifier `ag/claude-sonnet-4-6`. 17/18 defective cases completed successfully; CAND-0008 failed due to LLM JSON escape parsing error.
- **Config D (Contextual Hybrid):** Historical pilot run executed on 2026-10-10 against gateway identifier `ag/claude-sonnet-4-6`. 15/18 defective cases completed successfully; 3 cases failed (CAND-0020 parsing error; CAND-0026 and CAND-0033 due to upstream HTTP 503 reset).
- **Gateway Model Identity Limitation:** The requested and configured model identifier is `ag/claude-sonnet-4-6`. The serving gateway reports this alias; specific underlying backend versioning or routing beyond this identifier cannot be independently verified from gateway HTTP responses alone.
- **Live Execution Transport Evidence:** During live execution of clean controls, an internal 500 error occurred at step 11547 and was recovered via client-side exponential retry. While case outcomes completed as success, the execution transport history was retry-recovered rather than failure-free.
- **Inference Cost Accounting:** Config B incurred $0.2308 and Config C incurred $0.1989 across 18 reviews. Config D cost was unrecorded during live execution due to telemetry omission. The total known live cost lower bound is $0.4297 (Config D cost is additional).
- **Offline Evaluation Mode:** In offline evaluation mode, historical pilot outputs are loaded from frozen run artifacts (`data/results/config_*_pilot_run.json`). No live models were re-queried for pilot cases.

### Scientific Validity Rules & Metric Eligibility:
1. **Isolation of Mock Validation:** In offline mode, the 18 clean controls for Configurations B, C, and D are evaluated using `MockEvaluationLlmClient`. Mock outputs validate test pipeline mechanics and schema compliance, but **MUST NEVER be reported or interpreted as empirical model false-positive rates (0.00%)**. Therefore, Clean-case FPR for Config B, C, and D is strictly classified as **Unavailable (Mock)**.
2. **Ground-Truth Completeness Distinction:**
   - **Historical Pilot Cases (`CAND-0001` to `CAND-0033`):** Annotation completeness is **`partial`**. Each candidate is a real repository file where only the primary target CVE/defect locus was annotated. Unmatched predictions outside the locus are classified as **unadjudicated candidate findings**, not confirmed false positives.
   - **Clean Control Cases (`CTRL-0001` to `CTRL-0018`):** Annotation completeness is **`exhaustive`**. Each control is a small, self-contained deterministic Python fixture audited for Categories 1–6 with 0 SAST alerts. Findings emitted on clean controls represent observed candidate alerts on code intended to be clean, which have not undergone third-party manual panel adjudication.
3. **Config A Clean Specificity Caveat:** Config A achieves 0.00% warning rate on the 18 clean controls via deterministic SAST. This is valid evidence of tool specificity on this curated sample, but must not be generalized to arbitrary production repositories.

---

## 2. Benchmark Dataset Composition

| Dataset Partition | Cases Count | Ground Truth Defects | Annotation Completeness | Description |
| :--- | :---: | :---: | :---: | :--- |
| **Verified Defective Pilot Cases** | `18` | 23 defects | `partial` | Sourced from popular Python repositories (Django, FastAPI, Tornado, etc.) |
| **Verified Clean Control Cases** | `18` | 0 defects | `exhaustive` | Deterministic, secure Python fixtures paired with pilot categories |
| **Total Cases in Manifest** | `36` | 23 defects | Mixed | Full benchmark cohort for evaluation |

---

## 3. Aggregate Performance Metrics Comparison

| Metric | Config A (Static) | Config B (LLM Only) | Config C (Hybrid) | Config D (Repo Context) |
| :--- | :---: | :---: | :---: | :---: |
| **Cases Attempted** | 18 | 18 | 18 | 18 |
| **Cases Successful** | 18 | 18 | 18 | 18 |
| **Execution Status / Failures** | 0 failed / 0 partial | 0 failed / 0 partial | 0 failed / 0 partial | 0 failed / 0 partial |
| **True Positives (TP)** | 0 | 0 | 0 | 0 |
| **Observed Clean-Control Findings (Unadjudicated)** | 0 | 6 | 8 | 4 |
| **Unadjudicated Predictions (Pilot Cases)** | 0 | 0 | 0 | 0 |
| **Historical Naive FP (Total Unmatched)** | 0 | 6 | 8 | 4 |
| **False Negatives (FN)** | 0 | 0 | 0 | 0 |
| **Clean-Control Case Alert Rate** | **0.00%** *(curated sample)* | **16.67%** *(curated sample)* | **33.33%** *(curated sample)* | **11.11%** *(curated sample)* |
| **Recall (Defect Level)** | N/A | N/A | N/A | N/A |
| **Defect Case Detection Rate** | N/A | N/A | N/A | N/A |
| **Confirmed Precision** | N/A | **0.00%** | **0.00%** | **0.00%** |
| **Historical Naive Precision (Proxy)** | N/A | **0.00%** | **0.00%** | **0.00%** |
| **Historical Naive F1 Score (Proxy)** | N/A | N/A | N/A | N/A |

---

## 4. Defective Pilot Cohort vs Clean Control Separation

The current evaluation run evaluated exclusively the **18 clean control fixtures** (`CTRL-0001` to `CTRL-0018`). All 18 cases completed successfully across all 4 configurations without execution failure.

To maintain rigorous ground-truth separation and prevent conflating clean-case alert rates with defect recall, historical defect recall from the canonical common 14-case defective pilot benchmark (19 gold defects across cases where all configurations completed) is documented below as a distinct historical baseline:

| Metric (14 Common Defective Cases) | Config A (Static) | Config B (LLM Only) | Config C (Hybrid) | Config D (Repo Context) |
| :--- | :---: | :---: | :---: | :---: |
| **True Positives (TP)** | 3 | 5 | 7 | 7 |
| **False Negatives (FN)** | 16 | 14 | 12 | 12 |
| **Defect-Level Recall (%)** | **15.79%** (3/19) | **26.32%** (5/19) | **36.84%** (7/19) | **36.84%** (7/19) |
| **Historical Naive FP (Unadjudicated)** | 110 | 60 | 66 | 69 |
| **Historical Naive Precision (%)** | **2.65%** | **7.69%** | **9.59%** | **9.21%** |
| **Historical Naive F1 Score (%)** | **4.55%** | **11.90%** | **15.22%** | **14.74%** |

**Defensible Scientific Observations on Common Subset:**
- **Defect Recall Parity:** Configurations C and D both detect exactly 7/19 defects (**36.84% recall**). Repository context in Config D produced zero additional true positives over Config C.
- **Prediction Volume & Noise:** Config D produced 69 candidate predictions compared to 66 for Config C (delta +3).
- **Reliability & Overhead:** In historical defective evaluation, Config D suffered 3 pipeline failures (1 schema syntax error, 2 HTTP 503 resets) vs 1 failure for Config C, with ~3.2x longer execution duration.
- **Scientific Adjudication Requirement:** Declaring Config C definitively superior in precision or Config D worse requires expert adjudication of the 66 vs 69 candidate findings.

---

## 5. Configuration C Detailed Triage Analysis

| Triage Metric | Count | Description |
| :--- | :---: | :--- |
| **Static Findings Preserved** | `0` | All detected static findings retained without silent deletion |
| **Confirmed by LLM** | `0` | Static findings verified as reachable, genuine defects |
| **Triaged Likely False Positives** | `0` | Static findings refuted with technical rationale |
| **Inconclusive Findings** | `0` | Findings lacking sufficient local context to confirm |
| **Additional LLM Candidates** | `8` | Novel defects flagged by LLM not detected by static analysis |
| **Correct False-Positive Refutations** | `0` | Static FPs successfully identified and triaged by LLM |

---

## 6. Case-by-Case Provenance & Metric Eligibility Matrix

| Case ID | Partition | GT Completeness | Config A Prov | Config B Prov | Config C Prov | Config D Prov | Recall Eligible | Clean FPR Eligible |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `CAND-0001` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0002` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0007` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0009` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0014` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0017` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0019` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0021` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0025` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0027` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0031` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0032` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0006` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0008` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0015` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0020` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0026` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CAND-0033` | Pilot | `partial` | N/A | N/A | N/A | N/A | Yes | No (buggy) |
| `CTRL-0001` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0002` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0003` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0004` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0005` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0006` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0007` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0008` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0009` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0010` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0011` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0012` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0013` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0014` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0015` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0016` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0017` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |
| `CTRL-0018` | Clean | `exhaustive` | `real_deterministic` (success) | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Yes (evaluated configs) |

---

## 7. Threats to Scientific Validity & Thesis Readiness

1. **Mock Validation vs Empirical False-Positive Rate:** In offline mode, clean controls use mock LLM responses to verify test mechanics, which cannot establish empirical false-positive rates. When live API inference is run, empirical clean-case false-positive rates are directly observed and reported on the curated sample.
2. **Context Scope on Standalone Fixtures:** Clean control fixtures are independent Python files located in `data/fixtures/clean_controls/`. When Config D builds an AST index over this directory, it indexes sibling test fixtures rather than an integrated repository. In multiple cases (`CTRL-0003`, `CTRL-0013`, `CTRL-0016`), retrieved context was completely empty. In other cases (`CTRL-0001`, `CTRL-0012`), context consisted of accidental symbol collisions across unrelated fixtures. Therefore, the observed reduction in candidate findings from 8 in Config C to 4 in Config D cannot be causally attributed to caller/repository context; it reflects prompt structure and stochastic variance.
3. **Unadjudicated Negative Space & Observed Clean Findings:** Historical pilot cases only annotate the primary bug locus (`partial` completeness). Observed findings outside the locus and findings emitted on clean controls represent candidate alerts that have not undergone independent third-party manual panel adjudication.
4. **Telemetry Accounting & Cost Lower Bound:** Config D execution telemetry did not record USD cost. The total known live inference cost across Config B and Config C is $0.4297, which serves as an empirical lower bound for the live experiment.
5. **Gateway Model Identity Limitation:** The model identifier `ag/claude-sonnet-4-6` is an endpoint alias. Specific backend versioning beyond this alias cannot be independently verified from gateway HTTP responses alone.
6. **Thesis Recommendation:** Present Config C as the primary defensible hybrid architecture. Report clean-control alert rates alongside pilot recall, explicitly separate clean specificity from defect recall, and avoid causal claims regarding repository context on standalone fixtures.
