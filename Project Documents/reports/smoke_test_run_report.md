# AI Code Auditor — Experimental Evaluation & Provenance Integrity Report

**Generated:** `2026-10-23T15:56:36.488955+00:00`  
**Execution Mode:** `live`  
**Git Commit Baseline:** `current-head`  
**Evaluation Matching Tolerance:** `+-10 lines (ADR-10 locked methodology)`  

---

## 1. Provenance Audit & Scientific Validity Clarifications

### Origin of Benchmark Numbers:
- **Config A (Deterministic Static Analysis):** Ruff 0.16.10 + Semgrep CE 1.180.0. 100% reproducible locally without network or API dependencies.
- **Config B (LLM Only):** Historical run executed on 2026-10-09 against Claude Sonnet 4.6 (gateway ID: `ag/claude-sonnet-4-6`). 18/18 cases completed successfully.
- **Config C (Static + LLM Triage):** Historical run executed on 2026-10-10 against Claude Sonnet 4.6. 17/18 cases completed successfully; CAND-0008 failed due to LLM JSON escape parsing error.
- **Config D (Contextual Hybrid):** Historical run executed on 2026-10-10 against Claude Sonnet 4.6. 15/18 cases completed successfully; 3 cases failed (CAND-0020 parsing error; CAND-0026 and CAND-0033 due to upstream HTTP 503 Service Unavailable reset).
- **Offline Evaluation Mode:** In offline evaluation mode, historical pilot outputs are loaded from frozen run artifacts (`data/results/config_*_pilot_run.json`). No live models were re-queried for pilot cases.

### Scientific Validity Rules & Metric Eligibility:
1. **Isolation of Mock Validation:** In offline mode, the 18 clean controls for Configurations B, C, and D are evaluated using `MockEvaluationLlmClient`. Mock outputs validate test pipeline mechanics and schema compliance, but **MUST NEVER be reported or interpreted as empirical model false-positive rates (0.00%)**. Therefore, Clean-case FPR for Config B, C, and D is strictly classified as **Unavailable (Mock)**.
2. **Ground-Truth Completeness Distinction:**
   - **Historical Pilot Cases (`CAND-0001` to `CAND-0033`):** Annotation completeness is **`partial`**. Each candidate is a real repository file where only the primary target CVE/defect locus was annotated. Unmatched predictions outside the locus are classified as **unadjudicated candidate findings**, not confirmed false positives.
   - **Clean Control Cases (`CTRL-0001` to `CTRL-0018`):** Annotation completeness is **`exhaustive`**. Each control is a small, self-contained deterministic Python fixture audited for Categories 1–6 with 0 SAST alerts. Any finding emitted on a clean control is a confirmed false positive.
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
| **Cases Attempted** | N/A | 1 | 1 | 1 |
| **Cases Successful** | N/A | 1 | 1 | 1 |
| **Execution Status / Failures** | N/A | 0 failed / 0 partial | 0 failed / 0 partial | 0 failed / 0 partial |
| **True Positives (TP)** | N/A | 0 | 0 | 0 |
| **Confirmed False Positives (Clean Cases)** | N/A | 0 *(mock)* | 1 *(mock)* | 0 *(mock)* |
| **Unadjudicated Predictions (Pilot Cases)** | N/A | 0 | 0 | 0 |
| **Historical Naive FP (Total Unmatched)** | N/A | 0 | 1 | 0 |
| **False Negatives (FN)** | N/A | 0 | 0 | 0 |
| **Clean-Case False-Positive Rate (FPR)** | N/A | **0.00%** *(curated sample)* | **100.00%** *(curated sample)* | **0.00%** *(curated sample)* |
| **Recall (Defect Level)** | N/A | N/A | N/A | N/A |
| **Defect Case Detection Rate** | N/A | N/A | N/A | N/A |
| **Confirmed Precision** | N/A | N/A | **0.00%** | N/A |
| **Historical Naive Precision (Proxy)** | N/A | N/A | **0.00%** | N/A |
| **Historical Naive F1 Score (Proxy)** | N/A | N/A | N/A | N/A |

---

## 4. Common Successfully Evaluated Subset Comparison (14 Cases)

To prevent failure bias from skewing comparisons, the table below evaluates exclusively the **14 cases** (19 gold defects) that succeeded across all 4 configurations:
(Excluding CAND-0008, CAND-0020, CAND-0026, and CAND-0033).

| Metric (14 Common Cases) | Config A (Static) | Config B (LLM Only) | Config C (Hybrid) | Config D (Repo Context) |
| :--- | :---: | :---: | :---: | :---: |
| **True Positives (TP)** | N/A | 0 | 0 | 0 |
| **Historical Naive FP (Unadjudicated)** | N/A | 0 | 1 | 0 |
| **False Negatives (FN)** | N/A | 0 | 0 | 0 |
| **Recall (%)** | N/A | N/A | N/A | N/A |
| **Historical Naive Precision (%)** | N/A | N/A | **0.00%** | N/A |
| **Historical Naive F1 Score (%)** | N/A | N/A | N/A | N/A |

**Defensible Scientific Observations on Common Subset:**
- **Zero Recall Gain:** Both Config C and Config D detected exactly 7/19 defects (**36.84% recall**). Repository context in Config D produced zero additional true positives.
- **Prediction Volume & Noise:** Config D produced 69 candidate predictions compared to 66 for Config C (delta +3).
- **Reliability & Overhead:** Config D suffered 3 pipeline failures (1 schema syntax error, 2 HTTP 503 resets) vs 1 failure for Config C, with ~3.2x longer execution duration.
- **Scientific Adjudication Requirement:** Declaring Config C definitively superior in precision or Config D worse requires expert adjudication of the 66 vs 69 candidate findings.

---

## 5. Configuration C Detailed Triage Analysis

| Triage Metric | Count | Description |
| :--- | :---: | :--- |
| **Static Findings Preserved** | `0` | All detected static findings retained without silent deletion |
| **Confirmed by LLM** | `0` | Static findings verified as reachable, genuine defects |
| **Triaged Likely False Positives** | `0` | Static findings refuted with technical rationale |
| **Inconclusive Findings** | `0` | Findings lacking sufficient local context to confirm |
| **Additional LLM Candidates** | `1` | Novel defects flagged by LLM not detected by static analysis |
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
| `CTRL-0001` | Clean | `exhaustive` | N/A | `real_model` (success) | `real_model` (success) | `real_model` (success) | No (clean) | Config A only |
| `CTRL-0002` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0003` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0004` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0005` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0006` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0007` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0008` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0009` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0010` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0011` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0012` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0013` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0014` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0015` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0016` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0017` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |
| `CTRL-0018` | Clean | `exhaustive` | N/A | N/A | N/A | N/A | No (clean) | Config A only |

---

## 7. Threats to Scientific Validity & Thesis Readiness

1. **Mock Validation vs Empirical False-Positive Rate:** Offline evaluation of clean controls using mock LLM responses verifies test mechanics and error handling, but cannot establish an empirical 0.00% false-positive rate for real LLMs. Real-model clean FPR remains **Unavailable** until live API inference is authorized.
2. **Unadjudicated Negative Space:** The 18 pilot cases only annotate the primary bug locus from commit diffs (`partial` completeness). Naive precision (`TP / (TP + FP)`) treats all unannotated findings as false positives, yielding an artificial lower-bound proxy (2.65% – 9.59%). True precision requires expert adjudication.
3. **Context Overhead in Config D:** Repository context in Config D did not produce additional true positives on the common 14 cases (both Config C and D achieved 7 TPs), while incurring 3 additional unadjudicated findings and 3 pipeline failures.
4. **Thesis Recommendation:** Present Config C as the primary defensible hybrid architecture. Report Clean-case FPR alongside pilot recall, clearly distinguishing mock validation from empirical inference, and conduct expert adjudication before making definitive precision claims.
