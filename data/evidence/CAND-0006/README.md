# CAND-0006: Primary Source Evidence & Reproducibility Package

## 1. Overview
- **Candidate ID**: `CAND-0006`
- **Category**: Category 1 — Boundary / Conditional / Logic
- **Impact**: `functional`
- **Repository**: `scrapy/scrapy` ([https://github.com/scrapy/scrapy](https://github.com/scrapy/scrapy))
- **Buggy Commit**: `f02c3d1dcf3e4880388d19e961e7911be5dc54ff`
- **Fixed Commit**: `439a3e59b8e858441f8d97dbc32f398db392330d`
- **Affected File**: `scrapy/utils/datatypes.py`
- **Pre-Fix Locus**: Lines 318–319 (`while len(self) >= self.limit:` / `self.popitem(last=False)`)
- **Primary CWE**: `CWE-476` (NULL Pointer / NoneType Dereference)
- **Acceptable Alternative CWEs**: `["CWE-670"]` (Always-Incorrect Control Flow Implementation)
- **Reproducer Status**: `executed_confirmed`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A

---

## 2. Defect Description & Root Cause
In `scrapy/utils/datatypes.py`, class `LocalCache` inherits from `collections.OrderedDict`.
Its constructor accepts an optional `limit` parameter defaulting to `None`:
```python
    def __init__(self, limit=None):
        super(LocalCache, self).__init__()
        self.limit = limit
```
In `__setitem__`, the eviction loop checked:
```python
    def __setitem__(self, key, value):
        while len(self) >= self.limit:
            self.popitem(last=False)
        super(LocalCache, self).__setitem__(key, value)
```
When instantiated without arguments (`cache = LocalCache()`), `self.limit` is `None`.
On the very first item assignment (`cache['key'] = value`), Python evaluates `len(self) >= None`.
In Python 3, relational comparisons between integers and `None` raise:
`TypeError: '>=' not supported between instances of 'int' and 'NoneType'`.

---

## 3. Upstream Fix Commit
In upstream commit `439a3e59b8e858441f8d97dbc32f398db392330d` ("Fix scrapy.utils.datatypes.LocalCache limit issue"):
```diff
--- a/scrapy/utils/datatypes.py
+++ b/scrapy/utils/datatypes.py
@@ -315,8 +315,9 @@ class LocalCache(collections.OrderedDict):
         self.limit = limit
 
     def __setitem__(self, key, value):
-        while len(self) >= self.limit:
-            self.popitem(last=False)
+        if self.limit:
+            while len(self) >= self.limit:
+                self.popitem(last=False)
         super(LocalCache, self).__setitem__(key, value)
```
An explicit boundary guard (`if self.limit:`) was added before the eviction loop, preventing the comparison when `self.limit` is `None`.

Upstream unit tests were added in `tests/test_utils_datatypes.py`:
- `LocalCacheTest.test_cache_with_limit`
- `LocalCacheTest.test_cache_without_limit`

---

## 4. Local Reproducibility Execution
The script `reproduce_cand_0006.py` extracts raw file bytes directly from the Git blob store at commits `f02c3d1dcf` and `439a3e59b8`, instantiates `LocalCache()` without limit, and verifies:
1. **Buggy Revision**: Raises `TypeError: '>=' not supported between instances of 'int' and 'NoneType'` on insertion.
2. **Fixed Revision**: Successfully inserts items into cache without errors.

Execution results are recorded in `results.json` (`reproduced: true`, `reproducer_status: "executed_confirmed"`).

---

## 5. Phase 3C Replacement Rationale
In Phase 3A (Session 32), the student formally approved replacing `CAND-0003` (`cookiecutter/generate.py:85`) because missing an explicit `encoding='utf-8'` is an I/O locale/decoding flaw (CWE-176) rather than a clean fit for locked Category 1 (Boundary / Conditional / Logic) domain logic. Furthermore, CAND-0003's upstream reproducer was blocked due to missing `binaryornot`.

`CAND-0006` was selected as the replacement because:
1. It is a genuine Category 1 NoneType boundary/condition defect.
2. It has an atomic 2-line patch (`if self.limit:`).
3. It has a verified upstream unit test and executed/confirmed local reproducer (`reproducer_status = executed_confirmed`).
4. It is in a self-contained utility module (`scrapy/utils/datatypes.py`) of 330 lines (~2,800 tokens), perfectly fitting Tier 1 of the whole-file analysis protocol ($B_{\text{source}} = 16,000$ tokens).
5. All 8 conditions of the Admission Gate are fully satisfied.
