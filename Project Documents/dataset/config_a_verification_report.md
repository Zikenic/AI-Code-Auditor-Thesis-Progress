# Phase 3B.4 — Configuration A Baseline Verification & Approved Decisions Report

**Workspace:** `D:\Khai Van\KhaiVan Data\CODE\AI_Code_Auditor_Thesis1`
**Date:** October 9, 2026
**Scope:** Final integrity verification of Configuration A (Deterministic Static-Analysis Baseline), recording of approved student decisions on evaluation scope and private Semgrep rule-pack usage, unambiguous separation of mechanical vs semantic metrics, and formalization of the release gate.
**Baseline Commits:**
- Ruleset Freeze: `5406bb5`
- Static-Analysis Implementation: `d2e86d8`
- Pilot Benchmark Run: `486fc68`
- Phase 3B Documentation: `c1473a9`
- Phase 3B.1 Verification: `06810f4`
- Phase 3B.2 Scope & Rubric v1.0: `e4b3b9d`, `cd7201f`, `386e1dd`
- Phase 3B.3 Gate Resolution: `0246ee8`

---

## 1. Executive Summary & Authoritative Verdicts

### Verdict 1: Configuration A Baseline Evaluation Artifact
**VERDICT: ACCEPT WITH DOCUMENTED LIMITATIONS**
The raw Configuration A benchmark evaluation artifact ([`data/results/config_a_pilot_run.json`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/data/results/config_a_pilot_run.json)) is cryptographically verified, achieves 100% agreement with canonical ground truth across all 17 pilot cases, and remains immutable. Zero retrospective tuning was performed.

### Verdict 2: Common Input Scope for 17-Case Development Pilot
**VERDICT: APPROVED — OPTION 1 (WHOLE-FILE / COMPONENT AUDIT)**
The student has formally approved **Option 1 — Whole-File / Component Audit** for the 17-case development pilot:
- Configurations A–D will evaluate the exact same authentic pre-fix source snapshot ($C_{buggy}$) for controlled comparison.
- Configuration A's whole-file results serve as the frozen historical baseline.
- The overarching thesis objective remains an automated Pull Request auditing pipeline; the final PR-specific benchmark evaluation will be addressed during final benchmark curation ($\ge 100$ cases) via a defensible, non-circular input construction method.

### Verdict 3: Operational Local Use of Semgrep Rule Pack
**VERDICT: DIRECTED BY STUDENT FOR PRIVATE LOCAL RESEARCH**
The student has directed the project to continue using the existing frozen Semgrep rule pack (`python_security.yaml`) in the private local research environment:
- Pinned source revision, SHA-256 checksums, and ruleset identity are preserved.
- Git history inspection confirmed `python_security.yaml` was committed at `5406bb5` and exists in repository history.
- The repository and its Git history **must not be published or pushed to a public remote as-is**.
- Future public release may require a sanitized repository or a separately approved history-cleaning plan, not merely deleting the current YAML file.
- The public release and distribution gate remains open pending adequate licensing resolution.

---

## 2. Canonical Ground-Truth Reconciliation (Check 3.1: PASS)

An automated deterministic parity verification script ([`data/evidence/config_a_verification/verify_all_17_cases.py`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/data/evidence/config_a_verification/verify_all_17_cases.py)) evaluated every field of all 17 ground-truth verified cases between `data/pilot_cases.json` and `data/results/config_a_pilot_run.json`.

### Reconciliation Audit Table (All 17 Evaluated Cases)

| Case ID | Target Repository | Commit SHA | Target File | Canonical Loci (`data/pilot_cases.json`) | Artifact Loci (`config_a_pilot_run.json`) | Primary CWE | Parity Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CAND-0001** | `tornadoweb/tornado` | `2ca8821d00` | `tornado/http1connection.py` | `[[390, 394]]` | `[[390, 394]]` | CWE-670 | **MATCH** |
| **CAND-0002** | `tiangolo/fastapi` | `210af1fd3d` | `fastapi/routing.py` | `[[498, 502]]` | `[[498, 502]]` | CWE-670 | **MATCH** |
| **CAND-0007** | `tiangolo/fastapi` | `90120dd6e8` | `fastapi/routing.py` | `[[182, 184]]` | `[[182, 184]]` | CWE-352 | **MATCH** |
| **CAND-0009** | `pallets/jinja` | `a7863ba9d3` | `src/jinja2/filters.py` | `[[250, 250], [292, 293]]` | `[[250, 250], [292, 293]]` | CWE-79 | **MATCH** |
| **CAND-0014** | `django/django` | `425718726b` | `django/db/models/functions/datetime.py` | `[[45, 51], [225, 236]]` | `[[45, 51], [225, 236]]` | CWE-89 | **MATCH** |
| **CAND-0017** | `tortoise/tortoise-orm` | `816ff00e98` | `tortoise/backends/mysql/executor.py` | `[[19, 45]]` | `[[19, 45]]` | CWE-89 | **MATCH** |
| **CAND-0019** | `aio-libs/aiohttp` | `33ccdfb0a1` | `aiohttp/web_urldispatcher.py` | `[[574, 576], [643, 645]]` | `[[574, 576], [643, 645]]` | CWE-22 | **MATCH** |
| **CAND-0021** | `encode/starlette` | `24c1fac62a` | `starlette/staticfiles.py` | `[[172, 172]]` | `[[172, 172]]` | CWE-22 | **MATCH** |
| **CAND-0025** | `jpadilla/pyjwt` | `24b29adfeb` | `jwt/algorithms.py` | `[[186, 197]]` | `[[186, 197]]` | CWE-347 | **MATCH** |
| **CAND-0027** | `lepture/authlib` | `bb7a315bef` | `authlib/jose/__init__.py` | `[[49, 49]]` | `[[49, 49]]` | CWE-347 | **MATCH** |
| **CAND-0031** | `jupyterhub/jupyterhub` | `b405361674` | `jupyterhub/apihandlers/users.py` | `[[265, 267], [328, 331]]` | `[[265, 267], [328, 331]]` | CWE-269 | **MATCH** |
| **CAND-0032** | `zulip/zulip` | `ea0b8cc011` | `zerver/lib/message.py` | `[[825, 827], [842, 856]]` | `[[825, 827], [842, 856]]` | CWE-863 | **MATCH** |
| **CAND-0008** | `Kludex/python-multipart` | `d3d16dae4b` | `multipart/multipart.py` | `[[72, 75]]` | `[[72, 75]]` | CWE-1333 | **MATCH** |
| **CAND-0015** | `django/django` | `6b178a3e93` | `django/contrib/postgres/aggregates/general.py` | `[[54, 58]]` | `[[54, 58]]` | CWE-89 | **MATCH** |
| **CAND-0020** | `pallets/werkzeug` | `50cfeebcb0` | `src/werkzeug/security.py` | `[[151, 157]]` | `[[151, 157]]` | CWE-22 | **MATCH** |
| **CAND-0026** | `paramiko/paramiko` | `aefd28a7f0` | `paramiko/transport.py` | `[[1822, 1828]]` | `[[1822, 1828]]` | CWE-287 | **MATCH** |
| **CAND-0033** | `zulip/zulip` | `b1007916b0` | `zerver/actions/typing.py` | `[[83, 85]]` | `[[83, 85]]` | CWE-863 | **MATCH** |

Parity audit output is preserved in [`data/evidence/config_a_verification/parity_audit_output.txt`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/data/evidence/config_a_verification/parity_audit_output.txt) (17/17 verified, 0 discrepancies).

---

## 3. Section 3 Provenance & Reproducibility Audit (Checks 3.1–3.9)

| Check ID | Verification Dimension | Target Artifact / Scope | Verdict | Key Finding |
| :--- | :--- | :--- | :--- | :--- |
| **3.1** | **Parity Audit** | Canonical Ground Truth vs Results Artifact | **PASS** | 100% agreement across repository, commit SHA, target file, CWE, and loci. |
| **3.2** | **Artifact Preservation** | `data/results/config_a_pilot_run.json` | **PASS** | `git diff 486fc68 HEAD -- data/results/` is completely empty. Blob SHA `0f37b7aa...` identical. Disk byte difference ($130,542$ vs $134,329$) is Windows CRLF checkout expansion. Normalized LF bytes identical. |
| **3.3** | **Ruleset Manifest SHA** | `ruleset_manifest.json` & Semgrep YAML | **PASS** | Manifest blob SHA `75e517be...` and Semgrep YAML blob SHA `ade11ff5...` identical to commit `5406bb5`. |
| **3.4** | **Execution Metadata** | Results schema audit | **PASS / DOCUMENTED** | `target_file`, `execution_status`, and `duration_seconds` are preserved. Tool exit codes and stderr not captured in historical JSON (documented schema limitation). |
| **3.5** | **Semgrep Rule License** | `rules/semgrep/python_security.yaml` | **STUDENT-DIRECTED LOCAL RESEARCH / RELEASE GATE OPEN** | Semgrep Rules License v1.0 restricts use to internal business purposes and prohibits public redistribution. Permitted in private local research per student decision; remote push blocked. |
| **3.6** | **Offline Operation** | Blackhole test (`HTTP_PROXY=http://127.0.0.1:9`) | **PASS** | Probe connection failed with `ConnectionRefused`. Ruff (code 1) and Semgrep (code 0) executed without network access. Complete offline capability confirmed. |
| **3.7** | **Clean-Checkout Reproducibility** | Full benchmark reproduction | **LIMITATION / DOCUMENTED** | Parity script reproduces cleanly from repository data. Full rerun of `run_config_a_pilot.py` requires `scratch/upstream_repos/`. Future work: build repo-fetching fixture script. |
| **3.8** | **Suppression Fixture Coverage** | `tests/test_suppression.py` hardening | **PASS** | Added test cases for rule-specific `# nosemgrep` tags and hardened workspace isolation against adversarial `per-file-ignores` in `ruff.toml` and `pyproject.toml`. All 9 suppression tests pass (105 total). |
| **3.9** | **Per-Rule FP Breakdown** | Distribution of 124 unmatched predictions | **PASS** | 12 rules generated all 124 FPs. Ruff `S101` (51) and `B904` (25) constitute 61.3% of all false positives. Semgrep generated 0 unmatched FPs. |

### Per-Rule False Positive Breakdown (124 Unmatched Predictions)

| Rule ID | Linter | Tool Description | Primary CWE | FP Count | Percentage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `S101` | Ruff | Use of `assert` detected | CWE-670 | 51 | 41.13% |
| `B904` | Ruff | `raise ... from err` missing in `except` | CWE-398 | 25 | 20.16% |
| `B006` | Ruff | Mutable default argument used | CWE-670 | 19 | 15.32% |
| `B008` | Ruff | Function call in default argument | CWE-670 | 15 | 12.10% |
| `S704` | Ruff | `markupsafe.Markup` usage detected | CWE-79 | 4 | 3.23% |
| `B009` | Ruff | `getattr` with constant attribute | CWE-398 | 2 | 1.61% |
| `S610` | Ruff | Django `extra()` call detected | CWE-89 | 2 | 1.61% |
| `B007` | Ruff | Loop control variable not used in loop body | CWE-398 | 2 | 1.61% |
| `S110` | Ruff | `try-except-pass` detected | CWE-398 | 1 | 0.81% |
| `S311` | Ruff | Standard pseudo-random generators not suitable for security | CWE-330 | 1 | 0.81% |
| `B023` | Ruff | Function definition inside loop binding variable | CWE-398 | 1 | 0.81% |
| `B010` | Ruff | `setattr` with constant attribute | CWE-398 | 1 | 0.81% |
| **Total** | | **12 Rules** | | **124** | **100.0%** |

---

## 4. Official Mechanical Results vs. Secondary Root-Cause Alignment Audit

To ensure scientific rigor and avoid misleading claims, the official primary evaluation under the locked mechanical matcher and the secondary semantic audit are unambiguously separated.

### 4.1 Official Primary Evaluation under the Locked Mechanical Matcher
Under the frozen evaluation harness (one-to-one maximum cardinality bipartite matching, $\pm 10$ line tolerance window, exact CWE/alternative match):
- **True Positives (TP):** **3** (CAND-0001 / CWE-670, CAND-0009 / CWE-79, CAND-0014 / CWE-89)
- **False Positives (FP):** **124** (unmatched predictions across the 17 files)
- **False Negatives (FN):** **19** (unconsumed ground-truth defects out of 22 total)
- **Precision:** **2.36%** ($3 / 127$)
- **Recall:** **13.64%** ($3 / 22$)
- **F1 Score:** **4.03%**

These metrics represent the authoritative, locked mechanical evaluation baseline for Configuration A. The three mechanical True Positives are **not** relabeled as False Positives in primary results.

### 4.2 Secondary Root-Cause Alignment Audit
The three mechanical True Positive matches were manually examined under [Root-Cause Alignment Rubric v1.0](root_cause_alignment_rubric.md):
1. **CAND-0001 (`tornadoweb/tornado`):**
   - *Target:* `tornado/http1connection.py`, Locus `[390, 394]`, `CWE-670`.
   - *Prediction:* Ruff `S101` at line 385 (`assert self._read_finished`).
   - *Classification:* **`PROXIMITY_ONLY`** (flags internal state assertion 5 lines before parsing loop; unrelated to HTTP Request Smuggling flaw).
2. **CAND-0009 (`pallets/jinja`):**
   - *Target:* `src/jinja2/filters.py`, Loci `[[250, 250], [292, 293]]`, `CWE-79`.
   - *Prediction:* Ruff `S704` at line 303 (`return markupsafe.Markup(...)`).
   - *Classification:* **`PROXIMITY_ONLY`** (flags return statement on exact 10-line boundary; misses XML attribute injection flaw).
3. **CAND-0014 (`django/django`):**
   - *Target:* `django/db/models/functions/datetime.py`, Loci `[[45, 51], [225, 236]]`, `CWE-89`.
   - *Prediction:* Semgrep `extends-custom-expression` at lines `206–216` (`class Now(Func)`).
   - *Classification:* **`PROXIMITY_ONLY`** (flags class declaration overlapping window by 1 line; misses SQL injection in `TruncBase.__init__`).

### 4.3 Semantic Reporting Discipline & Limitations:
- **Zero Root-Cause-Aligned Matches Among Reviewed Set:** Among the **three reviewed mechanical matches**, exactly **0 of 3** represented semantic detection of the root-cause defect.
- **Unadjudicated Predictions:** The remaining **124 unmatched predictions were not individually adjudicated** under the semantic rubric.
- **No Global Semantic Metrics:** We do **not** claim global semantic precision, recall, or F1 from these three reviewed predictions.
- **Single-Rater Retrospective Limitation:** This audit was conducted retrospectively by a single rater without double-blinding and serves as an exploratory diagnostic only.

---

## 5. Input Scope & Changed-Line Filter Analysis: Circularity Clarification

### 5.1 Distinct Scopes Formally Defined
1. **Original Whole-File Baseline (Primary Scope — Approved & Implemented):**
   - Scans the entire file at $C_{buggy}$ (127 predictions emitted).
   - Valid, defensible, and 100% reconstructable across all 17 cases.
   - Evaluates offline security auditing / whole-file vulnerability discovery.
2. **Defect-Locus Diagnostic Filter (Circular Diagnostic Only):**
   - Applied via [`tools/apply_changed_line_filter.py`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/tools/apply_changed_line_filter.py) using $C_{target} = L_{defect}$.
   - Results in **0 retained findings** (`data/results/config_a_changed_line_filtered_run.json`).
   - **Circularity Note:** This is an artificial locus-overlap probe testing whether whole-file findings intersected the exact bug lines. It must **not** be described as an authentic simulation of PR review or as evidence that static analysis has zero PR-diff signal.
3. **Final PR-Specific Benchmark Evaluation (Still Open for Final Dataset):**
   - Requires an authentic or defensible pull request diff construction.
   - Remains open for the final $\ge 100$ case benchmark scaling phase.

---

## 6. Verification of Zero-Finding Cases (Check 4: PASS)

Four pilot cases produced zero findings in Configuration A: CAND-0015, CAND-0017, CAND-0020, and CAND-0027. Tool execution logs confirm these were authentic negative results:

| Case ID | Repository | Target File | File Size (Lines) | Ruff Exit Code | Semgrep Exit Code | Semgrep Errors | Dispatcher Status | Verifiable Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CAND-0015** | `django/django` | `django/contrib/postgres/aggregates/general.py` | 63 | 0 | 0 | 0 | `success` | Authentic 0 findings |
| **CAND-0017** | `tortoise/tortoise-orm` | `tortoise/backends/mysql/executor.py` | 71 | 0 | 0 | 0 | `success` | Authentic 0 findings |
| **CAND-0020** | `pallets/werkzeug` | `src/werkzeug/security.py` | 161 | 0 | 0 | 0 | `success` | Authentic 0 findings |
| **CAND-0027** | `lepture/authlib` | `authlib/jose/__init__.py` | 73 | 0 | 0 | 0 | `success` | Authentic 0 findings |

All four files were successfully scanned by both Ruff and Semgrep with exit code 0.

---

## 7. Hardened Static Analysis Engine & Test Suite (Check 3.8: PASS)

- **Suppression Neutralization:** Tokenized suppression neutralization in `suppression.py` protects string literals while neutralizing comments (`# noqa`, `# nosem`, `# nosemgrep`, `# ruff: noqa`, `# flake8: noqa`).
- **Workspace Isolation:** Scans run inside temporary isolated directories, shielding files from target-repo configs (`ruff.toml`, `pyproject.toml`, `.semgrepignore`).
- **Deduplication:** Merges findings only when file, category, and primary CWE match.
- **Quality Gate:** **105 tests passing in 20.71s** (`uv run pytest`). Ruff lint/format clean.

---

## 8. Environmental, Cryptographic & Rules-License Release Gate

### Toolchain Versions
- **Ruff:** `0.16.10`
- **Semgrep:** `1.180.0` (Community Edition)
- **Python:** `3.12.10` (Windows x64)

### Cryptographic Artifact Hashes (SHA-256)
- `src/auditor/static_analysis/ruleset_manifest.json`: `f6f2db25...` (172,536 bytes)
- `src/auditor/static_analysis/rules/semgrep/python_security.yaml`: `8d37f1fc...` (603,623 bytes)
- `data/pilot_cases.json`: `6a5cc4b8...` (31,785 bytes)
- `data/results/config_a_pilot_run.json`: `18de0e31...` (134,329 bytes, CRLF normalized LF: 130,542 bytes)
- `data/results/config_a_changed_line_filtered_run.json`: `f2249c5b...` (13,110 bytes)

### Semgrep Rules License v1.0 Operational Status & Release Gate:
1. **Student Operational Direction:** The student directs the project to continue using the existing frozen Semgrep rule pack in the **private local research environment**.
2. **Git History Inspection Findings:**
   `git log --all --full-history -- src/auditor/static_analysis/rules/semgrep/python_security.yaml` confirmed that the restricted YAML file was committed at commit `5406bb5` and exists in repository Git history.
3. **Operational Restrictions:**
   - The vendored `python_security.yaml` must not be copied into the public progress repository, thesis appendix, public artifact bundle, or any distributable package.
   - The repository and its Git history **must not be published or pushed to a public remote as-is**.
   - Future public release may require a sanitized repository or a separately approved history-cleaning plan, not merely deleting the current YAML file.
   - This represents the student's operational decision to continue local research, **not confirmation that all forms of private academic use are legally authorized**.
   - Public release and distribution remain blocked pending licensing resolution.
4. **Historical Baseline Protection:**
   The existing Configuration A results remain a historical baseline tied to the original ruleset and mapping. If the ruleset changes in the future:
   - Create a new versioned ruleset and rule-to-CWE mapping.
   - Record source revision, retrieval date, licensing information, checksums, and configuration identity.
   - Commit the new version before running its evaluation.
   - Establish a separate, versioned Configuration A baseline for the new rules.
   - Preserve the old baseline without alteration; never mix results from different ruleset versions.
5. **Open Licensing Question (Configs C & D Rule Material Transmission Gate):**
   Configs C and D send restricted-pack rule IDs and/or rule messages to a hosted LLM provider. The licensing implications of transmitting this material remain unresolved and require review. This is recorded as an open question, not a legal conclusion of permissibility or impermissibility.

---

## 9. Calibrated Scientific Conclusions & Next-Task Sequence

### Standardized Scientific Conclusion for Thesis:
> **The observed results are consistent with the hypothesis that deterministic static analysis alone may miss defects requiring broader semantic or repository context. This preliminary pilot (development pilot baseline $n=17$, whole-file static-analysis scope) does not establish the superiority of LLM-based or hybrid auditing; the subsequent controlled comparisons are needed to test that hypothesis.**

### Benchmark Gating Status:
- Accepted benchmark cases remain strictly at **0 / 100**.
- The 17 evaluated cases serve strictly as a development pilot baseline.

### Authoritative Next-Task Sequence:
1. **Define the precise whole-file/component input specification for Configurations B–D.** Specify file/component selection, context boundaries, source snapshots, coordinate mapping, and treatment of missing or oversized inputs. Make the comparison scope reproducible.
2. **Phase 3C — CAND-0003 replacement.** Investigate and verify a clean Category 1 logic-defect candidate, preserve the rejected case's historical evidence, and update the canonical dataset only after the replacement meets the existing evidence gate.
3. **Configuration B specification and implementation.** Only after the input-scope specification is settled and CAND-0003's disposition is resolved, freeze the provider/model version, prompt template, and cost cap before running benchmark cases.
4. **Deferred independent alternative-ruleset research.** Retain this as a separately tracked future task. Do not block continued private historical research while it is deferred, but do not publish restricted artifacts or claim licensing clearance.
