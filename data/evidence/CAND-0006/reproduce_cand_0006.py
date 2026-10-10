#!/usr/bin/env python3
"""CAND-0006: Bounded Reproducibility Experiment for Scrapy LocalCache NoneType Boundary Defect.

Candidate:     CAND-0006
Category:      Category 1 — Boundary / Conditional / Logic
Repository:    scrapy/scrapy (https://github.com/scrapy/scrapy)
Buggy Commit:  f02c3d1dcf3e4880388d19e961e7911be5dc54ff
Fixed Commit:  439a3e59b8e858441f8d97dbc32f398db392330d
Affected File: scrapy/utils/datatypes.py
Pre-Fix Locus: Lines 318–319 (in LocalCache.__setitem__)
Primary CWE:   CWE-476 (NULL Pointer / NoneType Dereference)
Alt CWE Set:   ["CWE-670"] (Always-Incorrect Control Flow Implementation)

Root Cause:
In LocalCache.__init__, the 'limit' parameter defaults to None.
In LocalCache.__setitem__, the loop condition `while len(self) >= self.limit:`
was evaluated unconditionally. In Python, comparing an integer to None via '>='
raises `TypeError: '>=' not supported between instances of 'int' and 'NoneType'`.
The patch adds `if self.limit:` guarding the while loop.

This script executes the authentic upstream regression test logic
(tests/test_utils_datatypes.py::LocalCacheTest::test_cache_without_limit)
against the extracted source files for both buggy and fixed commits.
"""

from __future__ import annotations

import importlib.util
import json
import platform
import subprocess
import sys
import time
import types
from pathlib import Path
from typing import Any

EVIDENCE_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVIDENCE_DIR.parents[2]
SCRATCH_SCRAPY = REPO_ROOT / "scratch" / "upstream_repos" / "scrapy_scrapy"

BUGGY_COMMIT = "f02c3d1dcf3e4880388d19e961e7911be5dc54ff"
FIXED_COMMIT = "439a3e59b8e858441f8d97dbc32f398db392330d"
TARGET_FILE = "scrapy/utils/datatypes.py"


def extract_git_blob(commit_hash: str, file_path: str) -> str:
    """Extract raw file contents directly from git blob store."""
    if not SCRATCH_SCRAPY.exists():
        raise FileNotFoundError(f"Scrapy repo not found at {SCRATCH_SCRAPY}")
    cmd = ["git", "-C", str(SCRATCH_SCRAPY), "show", f"{commit_hash}:{file_path}"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
    return result.stdout


def load_datatypes_module(source_code: str, module_name: str) -> types.ModuleType:
    """Load datatypes module from source string with isolated environment."""
    # Stub minimal scrapy namespace so datatypes.py can import ScrapyDeprecationWarning
    scrapy_mod = types.ModuleType("scrapy")
    exceptions_mod = types.ModuleType("scrapy.exceptions")

    class ScrapyDeprecationWarning(Warning):
        pass

    exceptions_mod.ScrapyDeprecationWarning = ScrapyDeprecationWarning
    scrapy_mod.exceptions = exceptions_mod
    sys.modules["scrapy"] = scrapy_mod
    sys.modules["scrapy.exceptions"] = exceptions_mod

    spec = importlib.util.spec_from_loader(module_name, loader=None)
    module = importlib.util.module_from_spec(spec)
    exec(source_code, module.__dict__)
    return module


def test_cache(cache_cls: Any, has_limit: bool = False) -> tuple[bool, str]:
    """Execute test corresponding to test_cache_without_limit."""
    try:
        if has_limit:
            cache = cache_cls(limit=2)
            cache["a"] = 1
            cache["b"] = 2
            cache["c"] = 3
            if len(cache) != 2 or "a" in cache or "c" not in cache:
                return False, f"Unexpected cache state with limit: {list(cache.items())}"
            return True, "Success with limit"
        else:
            cache = cache_cls()
            for x in range(100):
                cache[str(x)] = x
            if len(cache) != 100:
                return False, f"Length mismatch: {len(cache)} != 100"
            return True, "Success without limit"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def run_reproducer() -> dict[str, Any]:
    print("=== CAND-0006 Reproducibility Verification ===")
    print(f"Python Runtime: {platform.python_implementation()} {platform.python_version()}")
    print(f"OS: {platform.system()} {platform.release()} ({platform.machine()})")

    # 1. Extract source blobs
    buggy_src = extract_git_blob(BUGGY_COMMIT, TARGET_FILE)
    fixed_src = extract_git_blob(FIXED_COMMIT, TARGET_FILE)

    print(f"Extracted buggy source from {BUGGY_COMMIT[:10]}: {len(buggy_src)} chars")
    print(f"Extracted fixed source from {FIXED_COMMIT[:10]}: {len(fixed_src)} chars")

    # 2. Load modules
    mod_buggy = load_datatypes_module(buggy_src, "datatypes_buggy")
    mod_fixed = load_datatypes_module(fixed_src, "datatypes_fixed")

    # 3. Test Buggy Revision without limit
    t0 = time.perf_counter()
    buggy_ok_nolimit, buggy_msg_nolimit = test_cache(mod_buggy.LocalCache, has_limit=False)
    buggy_time = time.perf_counter() - t0

    # 4. Test Buggy Revision with limit (should work even in buggy version)
    buggy_ok_limit, buggy_msg_limit = test_cache(mod_buggy.LocalCache, has_limit=True)

    # 5. Test Fixed Revision without limit
    t0 = time.perf_counter()
    fixed_ok_nolimit, fixed_msg_nolimit = test_cache(mod_fixed.LocalCache, has_limit=False)
    fixed_time = time.perf_counter() - t0

    # 6. Test Fixed Revision with limit
    fixed_ok_limit, fixed_msg_limit = test_cache(mod_fixed.LocalCache, has_limit=True)

    print("\n--- Execution Results ---")
    print("Buggy without limit (defect path):")
    print(f"  Success: {buggy_ok_nolimit} (Expected: False)")
    print(f"  Message: {buggy_msg_nolimit}")
    print(f"  Time:    {buggy_time:.6f}s")

    print("\nBuggy with limit (normal path):")
    print(f"  Success: {buggy_ok_limit} (Expected: True)")
    print(f"  Message: {buggy_msg_limit}")

    print("\nFixed without limit (defect path):")
    print(f"  Success: {fixed_ok_nolimit} (Expected: True)")
    print(f"  Message: {fixed_msg_nolimit}")
    print(f"  Time:    {fixed_time:.6f}s")

    print("\nFixed with limit (normal path):")
    print(f"  Success: {fixed_ok_limit} (Expected: True)")
    print(f"  Message: {fixed_msg_limit}")

    # Defect confirmed if:
    # 1. Buggy without limit fails with TypeError
    # 2. Fixed without limit succeeds
    reproduced = (not buggy_ok_nolimit) and ("TypeError" in buggy_msg_nolimit) and fixed_ok_nolimit

    results = {
        "candidate_id": "CAND-0006",
        "category_id": 1,
        "impact": "functional",
        "repository": "scrapy/scrapy",
        "buggy_commit": BUGGY_COMMIT,
        "fixed_commit": FIXED_COMMIT,
        "target_file": TARGET_FILE,
        "pre_fix_locus": [318, 319],
        "primary_cwe": "CWE-476",
        "acceptable_alternative_cwes": ["CWE-670"],
        "reproducer_status": "executed_confirmed" if reproduced else "executed_not_reproduced",
        "reproduced": reproduced,
        "buggy_run": {
            "without_limit_ok": buggy_ok_nolimit,
            "without_limit_result": buggy_msg_nolimit,
            "with_limit_ok": buggy_ok_limit,
            "execution_time_seconds": buggy_time,
        },
        "fixed_run": {
            "without_limit_ok": fixed_ok_nolimit,
            "without_limit_result": fixed_msg_nolimit,
            "with_limit_ok": fixed_ok_limit,
            "execution_time_seconds": fixed_time,
        },
        "environment": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "os": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
        },
    }

    results_file = EVIDENCE_DIR / "results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nWrote results to {results_file}")

    assert reproduced, "Defect reproduction failed!"
    print("\n[SUCCESS] CAND-0006 defect reproduction confirmed!")
    return results


if __name__ == "__main__":
    run_reproducer()
