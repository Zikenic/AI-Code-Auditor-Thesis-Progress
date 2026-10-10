# Cross-Configuration Evaluation Input-Scope and Changed-Line Filter Specification

**Version:** 3.0 (Approved Operational Decision — Phase 3B.4)
**Date:** October 9, 2026
**Status:** APPROVED FOR 17-CASE DEVELOPMENT PILOT (OPTION 1: WHOLE-FILE / COMPONENT AUDIT)
**Scope:** Defines the input-scope construction, line-coordinate conventions, circularity diagnostics, and approved comparison framework for Configurations A–D on the 17-case development pilot.

---

## 1. Problem Statement & Historical Evidence Reality

### 1.1 The Input Scope Disparity
In Phase 3B, Configuration A scanned entire source files (`target_file` at pre-fix commit $C_{buggy}$), emitting 127 predictions across 17 files. Configurations B, C, and D were envisioned in the thesis proposal as pull-request auditors that review code modifications (diff hunks) within context.

Comparing whole-file static analysis directly with diff-scoped LLM review introduces an inherent scope mismatch:
- Whole-file static analysis incurs false-positive penalties across thousands of lines of unmodified code.
- Diff-scoped review inherently restricts attention to modified lines, creating an artificial precision disparity unless an explicit, defensible common input scope is established.

### 1.2 Upstream Git Evidence Reality (All 17 Pilot Cases)
An empirical audit across all 17 ground-truth-verified pilot cases reveals:
1. **Pre-Fix Source Availability (17 / 17, 100%)**: The authentic source code of the affected file at the pre-fix commit ($C_{buggy}$) is 100% reconstructable and cryptographically verified.
2. **Authentic Introducer PRs (0 / 17, 0%)**: None of the 17 pilot vulnerabilities originated from an isolated, small, authentic pull request immediately preceding the pre-fix state. In reality, vulnerabilities existed in the codebases for months or years (e.g., Tornado HTTP connection parsing, Django aggregation functions, Paramiko SSH transport handlers). The commits that originally introduced the code occurred in ancient repository states with completely different line numbers, obsolete AST structures, and different surrounding code.
3. **Fix Commits vs Introducer Diffs**: The upstream Git history reliably records the **fixing commit** ($C_{fix}$) and its pre-fix parent ($C_{buggy}$). The diff $C_{buggy} \rightarrow C_{fix}$ represents the *defensive remediation patch*, not the bug-introducing pull request.

---

## 2. Approved Pilot Decision: Option 1 — Whole-File / Component Audit

The student has formally approved **Option 1 — Whole-File / Component Audit** for the 17-case development pilot.

### 2.1 Core Rules for the 17-Case Pilot
1. **Identical Pre-Fix Snapshot**: Configurations A–D will evaluate the exact same authentic pre-fix source snapshot ($C_{buggy}$) for the controlled pilot comparison.
2. **Configuration A Historical Baseline**: Configuration A's original whole-file results ([`data/results/config_a_pilot_run.json`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/data/results/config_a_pilot_run.json)) remain the authoritative historical baseline.
3. **Configuration B Input Scope**: Configuration B will evaluate the same pre-fix file (or an explicitly defined deterministic component input, e.g. enclosing function/class).
4. **Configuration C Input Scope**: Configuration C will augment the review with static-analysis findings while strictly preserving the same underlying case and input scope.
5. **Configuration D Input Scope**: Configuration D will augment the review with repository-level context while strictly preserving the same underlying case and input scope.
6. **No Fix-Source Leakage**: Review inputs must strictly exclude corrected source code from the fix commit $C_{fix}$, pull request discussion of the remediation, or any other information that leaks the vulnerability patch.
7. **Source-Line Coordinate Conventions**: Line coordinates remain 1-indexed and anchored strictly to the canonical pre-fix file at $C_{buggy}$.
8. **Bounded Context Rule**: If model token limits require bounded component context instead of the whole file, the extraction method must be deterministic (e.g., AST enclosing scope with $\pm N$ context lines) and documented alongside any resulting comparability limitations before running the evaluation.

### 2.2 Boundary of Approval
- **Applies to Development Pilot Only**: This decision governs the 17-case development pilot to ensure controlled, rigorous, and direct comparability across Configurations A–D without synthetic answer leakage.
- **Production PR Review Objective Preserved**: The overall thesis engineering objective remains a PR-based code review system. Evaluating Configurations B–D on authentic PR-diff hunks remains an open requirement that will be addressed during final benchmark scaling ($\ge 100$ cases) via a defensible, non-circular input construction method.

---

## 3. Construction of the Existing Changed-Line Filter & Circularity Classification

### 3.1 How Eligible Lines Were Constructed
In [`tools/apply_changed_line_filter.py`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/tools/apply_changed_line_filter.py), the eligible changed-line set $C_{target}$ is constructed as:
```python
c_target = set()
for d in case.defects:
  for line_no in range(d.start_line, d.end_line + 1):
    c_target.add(line_no)
```
- **Derived Exclusively from Ground-Truth Defect Loci**: Eligible lines were defined strictly as the exact lines of `case.defects` in `data/pilot_cases.json`.
- **Not from an Authentic Bug-Introducing PR**: 0 of the 17 cases use an authentic historical bug-introducing diff.
- **Not from the Fix Commit Diff**: The filter does not use the patch diff $C_{buggy} \rightarrow C_{fix}$.
- **Synthetic Locus Intersection**: The filter is an artificial line-intersection mask.

### 3.2 Classification as a Circular Diagnostic (Not PR-Diff Performance)
Because $C_{target}$ is defined identically as the ground-truth defect loci:
- The filter is a **circular diagnostic probe** asking: *"Did any static analysis prediction happen to intersect the exact ground-truth bug lines?"*
- The resulting metric (**0 retained findings**) indicates only that none of the 124 false positives and none of the 3 mechanical true positives (which occurred at line 385 vs [390, 394], line 303 vs [292, 293], and lines 206–216 vs [225, 236]) fell directly on the exact defect lines.
- **Circularity Clarification**: This result must **not** be described as a simulation of authentic PR review or as evidence that static analysis has zero PR-diff signal. In an authentic pull request modifying a feature or function (e.g. 30–100 lines), static analysis tools running on the modified hunk frequently emit valid linting, typing, or security diagnostics.
- The mechanically filtered artifact ([`data/results/config_a_changed_line_filtered_run.json`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/data/results/config_a_changed_line_filtered_run.json)) is preserved as a diagnostic record of defect-locus intersection, but must **not** be presented as an empirical measurement of PR-diff review performance.

---

## 4. Evaluation Scopes Distinguished

To prevent methodological confusion, three distinct evaluation scopes are strictly distinguished:

1. **Original Whole-File Baseline (Primary Scope — Approved & Implemented):**
   - Scans the entire file at $C_{buggy}$ (127 predictions emitted).
   - Valid, defensible, and 100% reconstructable across all 17 cases.
   - Evaluates offline security auditing / whole-file bug finding.
2. **Defect-Locus Diagnostic Filter (Secondary Diagnostic — Circular Diagnostic):**
   - Mechanically filters whole-file predictions by exact ground-truth defect loci ($C_{target} = L_{defect}$).
   - Diagnostic only; evaluates locus-coincidence of whole-file findings.
3. **Final PR-Specific Benchmark Evaluation (Secondary Scope — Still Open for Final Dataset):**
   - Requires a defensible, non-circular input construction (e.g., authentic introducer PRs in final $\ge 100$ dataset).
   - Currently, 0 of 17 pilot cases have an authentic historical PR diff.

---

## 5. Per-Case Scope Register (All 17 Pilot Cases)

| Case ID | Target Repository | Pre-Fix Commit ($C_{buggy}$) | Target File | Total Lines | Canonical GT Loci ($L_{defect}$) | Pilot Scope Status |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| **CAND-0001** | `tornadoweb/tornado` | `2ca8821d00` | `tornado/http1connection.py` | 842 | `[[390, 394]]` | **Approved Whole-File / Component** |
| **CAND-0002** | `tiangolo/fastapi` | `210af1fd3d` | `fastapi/routing.py` | 510 | `[[498, 502]]` | **Approved Whole-File / Component** |
| **CAND-0007** | `tiangolo/fastapi` | `90120dd6e8` | `fastapi/routing.py` | 425 | `[[182, 184]]` | **Approved Whole-File / Component** |
| **CAND-0009** | `pallets/jinja` | `a7863ba9d3` | `src/jinja2/filters.py` | 1459 | `[[250, 250], [292, 293]]` | **Approved Whole-File / Component** |
| **CAND-0014** | `django/django` | `425718726b` | `django/db/models/functions/datetime.py` | 415 | `[[45, 51], [225, 236]]` | **Approved Whole-File / Component** |
| **CAND-0017** | `tortoise/tortoise-orm` | `816ff00e98` | `tortoise/backends/mysql/executor.py` | 71 | `[[19, 45]]` | **Approved Whole-File / Component** |
| **CAND-0019** | `aio-libs/aiohttp` | `33ccdfb0a1` | `aiohttp/web_urldispatcher.py` | 1252 | `[[574, 576], [643, 645]]` | **Approved Whole-File / Component** |
| **CAND-0021** | `encode/starlette` | `24c1fac62a` | `starlette/staticfiles.py` | 246 | `[[172, 172]]` | **Approved Whole-File / Component** |
| **CAND-0025** | `jpadilla/pyjwt` | `24b29adfeb` | `jwt/algorithms.py` | 680 | `[[186, 197]]` | **Approved Whole-File / Component** |
| **CAND-0027** | `lepture/authlib` | `bb7a315bef` | `authlib/jose/__init__.py` | 73 | `[[49, 49]]` | **Approved Whole-File / Component** |
| **CAND-0031** | `jupyterhub/jupyterhub` | `b405361674` | `jupyterhub/apihandlers/users.py` | 931 | `[[265, 267], [328, 331]]` | **Approved Whole-File / Component** |
| **CAND-0032** | `zulip/zulip` | `ea0b8cc011` | `zerver/lib/message.py` | 1658 | `[[825, 827], [842, 856]]` | **Approved Whole-File / Component** |
| **CAND-0008** | `Kludex/python-multipart` | `d3d16dae4b` | `multipart/multipart.py` | 1893 | `[[72, 75]]` | **Approved Whole-File / Component** |
| **CAND-0015** | `django/django` | `6b178a3e93` | `django/contrib/postgres/aggregates/general.py` | 63 | `[[54, 58]]` | **Approved Whole-File / Component** |
| **CAND-0020** | `pallets/werkzeug` | `50cfeebcb0` | `src/werkzeug/security.py` | 161 | `[[151, 157]]` | **Approved Whole-File / Component** |
| **CAND-0026** | `paramiko/paramiko` | `aefd28a7f0` | `paramiko/transport.py` | 2673 | `[[1822, 1828]]` | **Approved Whole-File / Component** |
| **CAND-0033** | `zulip/zulip` | `b1007916b0` | `zerver/actions/typing.py` | 210 | `[[83, 85]]` | **Approved Whole-File / Component** |

---

## 6. Summary of Scope Coverage
- **Total Ground-Truth Verified Pilot Cases**: 17
- **Cases with Reconstructable Pre-Fix Snapshot ($C_{buggy}$)**: 17 (100%)
- **Next Step Operationalized**: The precise whole-file/component input specification for Configurations B–D is defined in [`Project Documents/dataset/configuration_input_protocol.md`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/Project%20Documents/dataset/configuration_input_protocol.md) (Phase 3B.5).
- **Next Step Before Implementation**: Phase 3C — CAND-0003 replacement in canonical dataset.
