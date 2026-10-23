# Real GitHub Verification & Pipeline Audit Report

**Date:** October 23, 2026  
**Environment:** Windows 11, Python 3.12.10, Pytest 9.1.1, Ruff 0.16.10, Semgrep CE 1.180.0  
**Tested Branch:** `test/real-github-pr-audit` (branched from `feat/github-pr-source-materialization` at commit `4338b94`)

---

## 1. Executive Summary

This report documents the verification of the AI Code Auditor backend intake and source acquisition pipeline against live GitHub remote infrastructure and real repositories, following the implementation in `feat/github-pr-source-materialization`.

The verification established:
1. **Live GitHub Network Access Succeeded (Public Remote)**: The system successfully fetched, materialized, analyzed, and persisted findings for real remote commits from GitHub (`Zikenic/AI-Code-Auditor-Thesis-Progress`) over the public internet with `allow_local_repos=False`.
2. **Critical Windows Locale Defect Discovered and Resolved**: On Windows, `subprocess.run` without explicit UTF-8 encoding defaulted to `cp1252`, causing a `UnicodeDecodeError` when processing diffs containing non-ASCII characters. This defect was fixed and verified with a regression test.
3. **Private Repository Live Testing Condition**: Live testing against private repositories is currently blocked because `GITHUB_TOKEN` is not set in `os.environ`. Per security instructions, no token was requested or fabricated.
4. **Offline Test Suite Integrity**: The complete offline test suite passes (173 passed, 0 failures), maintaining zero external network or credential dependencies.

---

## 2. Implementation Audit: Handling of Core Scenarios

| Scenario | Audit Finding | Code Reference |
| :--- | :--- | :--- |
| **1. Public Repositories** | Supported anonymously via HTTPS. No credentials injected into remote URLs. | `GitWorkspaceProvider._materialize_remote` (`git_provider.py:282`) |
| **2. Private Repositories** | Supported via optional `GITHUB_TOKEN` passed securely as HTTP extraHeader (`-c http.extraHeader="AUTHORIZATION: bearer <token>"`). | `GitWorkspaceProvider._materialize_remote` (`git_provider.py:295`) |
| **3. PR Head & Base SHAs** | Strict 40-hex SHA validation. Resolves and checks out `head_commit` while preserving `base_commit` for exact diff computation. | `validate_commit_sha` (`git_provider.py:112`) |
| **4. Fork-Originated PRs** | Targets `refs/pull/<pr_number>/head` on the target repository first, which GitHub automatically creates for all PRs (including fork PRs). | `git_provider.py:301-312` |
| **5. Missing Commits & Errors** | Subprocess errors captured, sanitized, and re-raised as domain exceptions (`CommitNotFoundError`, `GitCommandError`). Webhook background task transitions audit to `failed`. | `git_provider.py:222-225`, `processor.py:149-165` |
| **6. Workspace Cleanup** | Context manager `with provider.materialize(...)` uses `try ... finally` and Windows-safe `_remove_readonly` (`stat.S_IWRITE`) to guarantee 100% deletion of temporary directories. | `git_provider.py:90-109`, `git_provider.py:270` |
| **7. Credential Redaction** | `_sanitize_error_text()` scrubs tokens, Bearer headers, Basic auth, and embedded URL credentials from all logs and exception messages. | `git_provider.py:80-88` |
| **8. Webhook Idempotency** | Checks `X-GitHub-Delivery` against persisted audits. Duplicate delivery IDs return 202 Accepted without re-queueing background analysis. | `webhooks.py:161-173` |
| **9. PR Scope & Unchanged Files** | `py_files = [f for f in changed_files if f.endswith(".py")]`. Unchanged files are **never** passed to Ruff or Semgrep. Within changed files, full file is currently analyzed. | `engine.py:83-113` |
| **10. Status & Provenance** | Database records transitions `pending` $\rightarrow$ `running` $\rightarrow$ `completed` / `failed`, with `duration_seconds` and analyzed base/head commit provenance. | `processor.py:126-147` |

---

## 3. Real GitHub Verification vs. Offline Mocks

### 3.1. Exact Distinction

| Dimension | Offline Tests (`test_e2e_source_materialization.py`) | Real GitHub Verification (`test_full_live_audit`) |
| :--- | :--- | :--- |
| **Target Repository** | Local Git directory fixture created via `git init` on `tmp_path` | Real remote GitHub repository: `https://github.com/Zikenic/AI-Code-Auditor-Thesis-Progress.git` |
| **Network Access** | Completely offline (`allow_local_repos=True`) | Real live HTTPS traffic to `github.com` (`allow_local_repos=False`) |
| **Revisions Tested** | Synthetic commits with intentional vulnerabilities | Real published commits: HEAD `2d9083099d1a7356c893e1bbbad44c782d47b64d`, Base `d6200f7ad618edc84df13a01a07b0d891b3eea3f` |
| **Diff Extraction** | ~300 bytes local unified diff | 3,996,069 bytes (3.99 MB) real multi-file unified diff |
| **Findings Persisted** | 2 synthetic findings (Ruff S605, S607) | 360 real static findings persisted in database |
| **Duration** | ~0.5 seconds | 20.453 seconds |

### 3.2. Live Test Execution Details

- **Target Repository:** `Zikenic/AI-Code-Auditor-Thesis-Progress` (Public)
- **Head SHA:** `2d9083099d1a7356c893e1bbbad44c782d47b64d`
- **Base SHA:** `d6200f7ad618edc84df13a01a07b0d891b3eea3f`
- **Changed Files Count:** 183 files (79 Python `.py` files)
- **Configuration:** `AuditConfiguration.A` (Static Analysis baseline)
- **Audit Outcome:** Status `completed`, duration `20.453s`, error message `None`
- **Persisted Findings:** 360 findings normalized across Ruff rules (e.g., S603 subprocess calls, S101 assertions) and Semgrep Community Edition rules.
- **Resource Cleanup:** Temporary workspace directory `auditor_ws_*` verified deleted after execution.

---

## 4. Defect Discovered and Resolved

### Defect: Windows Default Locale Encoding Crash on Non-ASCII Diffs
- **Symptom:** During initial live clone of `Zikenic/AI-Code-Auditor-Thesis-Progress`, `_run_git(["diff", ...])` raised:
  `UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d in position 69601: character maps to <undefined>`.
- **Root Cause:** In `_run_git`, `subprocess.run` was called with `text=True` without explicitly specifying `encoding="utf-8"`. On Windows, the default locale is `cp1252`, which fails when diffs contain UTF-8 characters (e.g. smart quotes `“ ”`, mathematical symbols `± ≥ ≤`, or Vietnamese diacritics).
- **Resolution:** Updated `_run_git` to specify `encoding="utf-8", errors="replace"` and guaranteed fallback to empty string `proc.stdout or ""`.
- **Regression Test:** Added `test_materialize_utf8_diff_content` in `tests/test_git_provider.py` to prevent future regressions.

---

## 5. PR Scope Analysis (Unchanged Files vs Changed Files)

Section 4 of the task prompt raised the question of whether Config A analyzes the whole repository or only changed files:

1. **File-Level Isolation (Verified Compliant)**:
   [`StaticAnalysisEngine.run_static_analysis`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/src/auditor/static_analysis/engine.py#L77) explicitly filters:
   `py_files = [f for f in changed_files if f.endswith(".py")]`.
   Only these files are copied into [`ControlledSourceWorkspace`](file:///d:/Khai%20Van/KhaiVan%20Data/CODE/AI_Code_Auditor_Thesis1/src/auditor/static_analysis/suppression.py) and supplied as explicit path arguments to Ruff and Semgrep. **Unchanged files in the repository are never analyzed and never produce findings.**
2. **Line-Level Locus within Changed Files (Architectural Trade-off)**:
   Within a modified file, Ruff and Semgrep scan the entire content of that file. Consequently, if a pre-existing issue exists on an unmodified line of a modified file, it will be included in the findings for that file.
   - *Thesis Compliance*: This matches the architectural design in `system_architecture.md` (FR-03, ADR-10: $\pm 10$ line locus tolerance, intra-file matching).
   - *Future Enhancement*: When GitHub PR line-level review commenting is implemented in subsequent milestones, findings can optionally be filtered by diff hunk line ranges if comments are to be posted strictly inline.

---

## 6. Verification Results Summary

- **Targeted Provider Tests (`tests/test_git_provider.py`):** 17/17 passed.
- **Targeted Integration Tests (`tests/test_e2e_source_materialization.py`):** 2/2 passed.
- **Targeted Subsystem Tests (`webhooks`, `db`, `dispatcher`, `static_engine`):** 34/34 passed.
- **Full Test Suite:** 173 passed, 1 warning (deprecation warning from Starlette testclient).
- **Ruff Linter:** 0 errors, 0 warnings across all modified and new files.
