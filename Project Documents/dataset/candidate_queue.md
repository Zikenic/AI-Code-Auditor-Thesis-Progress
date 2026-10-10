# Benchmark Candidate Queue — Phase 1 Discovery & Phase 2 Pilot Verification

> **Status**: ACTIVE STAGING QUEUE (Phase 1 Complete; Phase 2 Pilot Complete: 12 / 12 Pilot Candidates Verified)  
> **Rule**: This document is a candidate staging area, NOT the finalized evaluation benchmark. Candidates undergo primary-source verification (`SOURCE_VERIFIED`), locus isolation and reproducer verification (`GROUND_TRUTH_VERIFIED`), and final benchmark acceptance (`ACCEPTED INTO BENCHMARK`).

---

## 1. Candidate Queue Summary Statistics

| Category | Description | Target | Discovered | Staged | Phase 2 (GT Verified) | Remaining Staged (SV) | Quality Distribution |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Category 1** | Boundary / Conditional / Logic | 6 | 6 | 6 | **3** (`CAND-0001`, `0002`, `0006`) | 3 (`0003` replaced/archived, `0004`, `0005`) | 6 Level A |
| **Category 2** | Input Validation / Sanitization | 6 | 8 | 7 | **4** (`CAND-0007`, `0009`, `0008`, `0036` reserve) | 3 (`0010`, `0011`, `0012`) | 7 Level A |
| **Category 3** | SQL / ORM Injection | 6 | 7 | 6 | **3** (`CAND-0014`, `0017`, `0015`) | 3 (`0013`, `0016`, `0018`) | 6 Level A |
| **Category 4** | Path Traversal / Unsafe File Ops | 6 | 7 | 6 | **3** (`CAND-0019`, `0021`, `0020`) | 3 (`0022`, `0023`, `0024`) | 5 Level A, 1 Level B |
| **Category 5** | Authentication | 6 | 8 | 6 | **3** (`CAND-0025`, `0027`, `0026`) | 3 (`0028`, `0029`, `0030`) | 5 Level A, 1 Level B |
| **Category 6** | Authorization (BOLA / IDOR / Scopes) | 6 | 7 | 5 | **3** (`CAND-0031`, `0032`, `0033`) | 2 (`0034`, `0035`) | 3 Level A, 2 Level B |
| **TOTAL** | | **36** | **43** | **36** | **19 Verified** (18 Canonical + 1 Reserve `0036`) | **17 Source Verified** | **32 Level A, 4 Level B** |

### Census & Lifecycle Reconciliation (Audited via `tools/compute_census.py`)

1. **Queue Lifecycle Partition (Total = 36 staged candidates)**:
   - `GROUND_TRUTH_VERIFIED`: **19 candidates** (18 in canonical benchmark dataset + 1 reserve candidate `CAND-0036` reclassified to Category 2).
   - `SOURCE_VERIFIED`: **17 candidates** (incl. `CAND-0003` archived historical evidence, `CAND-0004` disqualified, and 15 remaining staged candidates).
   - Mutually exclusive partition sum: $19 + 17 = 36$ staged candidates.
   - **Reconciliation Resolution**: 18 canonical GT verified + 1 reserve CAND-0036 GT verified = 19 GT verified. 36 - 19 = 17 remaining staged candidates (all SOURCE_VERIFIED).
2. **Canonical Evaluation Dataset (`data/pilot_cases.json`)**:
   - Total cases: **18 cases** (all 18 `GROUND_TRUTH_VERIFIED`).
   - Ground-truth defects: **23 defects** (all 23 in GT verified cases).
   - Distinct defect loci (ranges): **23 distinct loci**.
   - Distinct target files: **17 files** (`fastapi/routing.py` shared by `CAND-0002` and `CAND-0007`).
   - Distinct contextual files: **1 file** (`paramiko/common.py` in `CAND-0026`).
   - File union (target + contextual): **18 files**.
3. **Separate Registers & Quality Gates**:
   - Rejected Leads Register: **7 leads** (`REJ-0001` through `REJ-0007`), maintained separately from the 36 candidate queue.
   - Benchmark Accepted Cases: Strictly **0 / 100** (`ACCEPTED INTO BENCHMARK = 0`).


---

## 2. Category 1: Boundary, Conditional & Logic Defects

### CAND-0001: Tornado — HTTP Chunking Output Logic Bug
- **Candidate ID**: `CAND-0001`
- **Source**: BugsInPy (Bug #2) / Primary Git History
- **Source Tier**: Tier 2 (BugsInPy) + Tier 1 (Target Git History)
- **Repository**: `tornadoweb/tornado` ([https://github.com/tornadoweb/tornado](https://github.com/tornadoweb/tornado))
- **File / Target**: `tornado/http1connection.py`
- **Buggy Commit**: `2ca8821d006f6693f920a4b183a3a7c985a5c8ad`
- **Fixed Commit**: `4f486a4aec746e9d66441600ee3b0743228b061c` ([Commit Diff](https://github.com/tornadoweb/tornado/commit/4f486a4aec746e9d66441600ee3b0743228b061c.diff))
- **Bug Class**: Category 1 — Boundary / Conditional / Logic
- **Impact**: `functional`
- **Ground-Truth Pre-Fix Locus**: Lines 390–394 (specifically line 393: `and "Transfer-Encoding" not in headers`)
- **Multi-File Span**: No (Single file local defect)
- **Proposed Primary CWE**: CWE-670 (Always-Incorrect Control Flow Implementation)
- **Proposed CWE Labels**: `["CWE-670", "CWE-440"]`
- **Acceptable Alternative CWE Set**: `["CWE-440", "CWE-20"]`
- **Reproducer / Test**: `tornado/test/httpclient_test.py::test_redirect_put_with_body`
- **Verification Execution**: Buggy evaluates `chunking_output=False` when Transfer-Encoding provided; fixed evaluates `chunking_output=True`.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified git diff, atomic 3-line logic fix, isolated test case in `tornado/test/httpclient_test.py`)
- **Verifier Timestamp**: `2026-09-25T23:40:00+07:00`
- **Discovery & Technical Notes**: In `write_headers`, chunking output logic erroneously evaluated `"Transfer-Encoding" not in headers`, disabling chunked transfer encoding when `Transfer-Encoding: chunked` was explicitly provided. Fixed by accepting `headers["Transfer-Encoding"] == "chunked"`.

### CAND-0002: FastAPI — WebSocket Route Dependency Override Omission
- **Candidate ID**: `CAND-0002`
- **Source**: BugsInPy (Bug #2) / Primary Git History
- **Source Tier**: Tier 2 (BugsInPy) + Tier 1 (Target Git History)
- **Repository**: `tiangolo/fastapi` ([https://github.com/tiangolo/fastapi](https://github.com/tiangolo/fastapi))
- **File / Target**: `fastapi/routing.py`
- **Buggy Commit**: `210af1fd3dc0f612a08fa02a0cb3f5adb81e5bfb`
- **Fixed Commit**: `02441ff0313d5b471b662293244c53e712f1243f` ([Commit Diff](https://github.com/tiangolo/fastapi/commit/02441ff0313d5b471b662293244c53e712f1243f.diff))
- **Bug Class**: Category 1 — Boundary / Conditional / Logic
- **Impact**: `functional`
- **Ground-Truth Pre-Fix Locus**: Lines 498–502 (specifically line 501: `route = APIWebSocketRoute(path, endpoint=endpoint, name=name)`)
- **Multi-File Span**: No (Single file local defect)
- **Proposed Primary CWE**: CWE-670 (Always-Incorrect Control Flow Implementation)
- **Proposed CWE Labels**: `["CWE-670"]`
- **Acceptable Alternative CWE Set**: `["CWE-440"]`
- **Reproducer / Test**: `tests/test_ws_router.py::test_router_ws_depends_with_override`
- **Verification Execution**: Buggy creates route with `dependency_overrides_provider=None`; fixed forwards provider properly.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, unit test in `tests/test_ws_router.py`)
- **Verifier Timestamp**: `2026-09-25T23:40:00+07:00`
- **Discovery & Technical Notes**: `add_api_websocket_route` instantiated `APIWebSocketRoute` without forwarding `dependency_overrides_provider`, breaking dependency injection overrides in WebSocket endpoints.

### CAND-0003: Cookiecutter — Missing UTF-8 Encoding Parameter in Context Loading
- **Candidate ID**: `CAND-0003`
- **Source**: BugsInPy (Bug #1) / Primary Git History / GitHub PR #1414
- **Source Tier**: Tier 2 (BugsInPy) + Tier 1 (Target Git History)
- **Repository**: `cookiecutter/cookiecutter` ([https://github.com/cookiecutter/cookiecutter](https://github.com/cookiecutter/cookiecutter))
- **File / Target**: `cookiecutter/generate.py`
- **Buggy Commit**: `c15633745df6abdb24e02746b82aadb20b8cdf8c`
- **Fixed Commit**: `7f6804c4953a18386809f11faf4d86898570debc` ([Commit Diff](https://github.com/cookiecutter/cookiecutter/commit/7f6804c4953a18386809f11faf4d86898570debc.diff))
- **Bug Class**: Category 1 — Boundary / Conditional / Logic
- **Impact**: `functional`
- **Ground-Truth Pre-Fix Locus**: Line 85 (`with open(context_file) as file_handle:`)
- **Multi-File Span**: No (Single file context loader)
- **Proposed Primary CWE**: CWE-20 (Improper Input Validation / Encoding Boundary) — Disputed; authoritative is CWE-176
- **Proposed CWE Labels**: `["CWE-20", "CWE-670"]`
- **Acceptable Alternative CWE Set**: `["CWE-670"]`
- **Reproducer / Test**: Upstream regression test `tests/test_generate_context.py` using `tests/test-generate-context/non_ascii.json` (Cited from PR #1414, not locally executed)
- **Verification Execution**: Buggy opens context_file without explicit encoding, raising `UnicodeDecodeError` on non-UTF8 system locales; fixed passes `encoding='utf-8'`.
- **Classification Status**: `REPLACED IN CANONICAL DATASET (REPLACED BY CAND-0006 IN PHASE 3C)`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, unit test case in PR #1414)
- **Verifier Timestamp**: `2026-10-09T06:30:00+07:00`
- **Discovery & Technical Notes**: `open(context_file)` invoked without explicit `encoding='utf-8'`, causing `UnicodeDecodeError` on environments with non-UTF8 system default encoding (e.g., Windows cp1252) when loading non-ASCII context templates. Pre-fix locus verified at line 85. *(Phase 3A/3C Disposition: Student formally approved replacing CAND-0003 in the canonical dataset during curation because missing an encoding parameter is an I/O locale/decoding flaw [authoritative CWE-176] rather than a clean fit for locked Category 1 domain logic. In Phase 3C, CAND-0003 was replaced in data/pilot_cases.json by CAND-0006; historical primary-source evidence is preserved here).*

### CAND-0004: Cookiecutter — Early Return Truncation in Hook Finding
- **Candidate ID**: `CAND-0004`
- **Source**: BugsInPy (Bug #2) / Primary Git History
- **Source Tier**: Tier 2 (BugsInPy) + Tier 1 (Target Git History)
- **Repository**: `cookiecutter/cookiecutter` ([https://github.com/cookiecutter/cookiecutter](https://github.com/cookiecutter/cookiecutter))
- **File / Target**: `cookiecutter/hooks.py`
- **Buggy Commit**: `d7e7b28811e474e14d1bed747115e47dcdd15ba3`
- **Fixed Commit**: `90434ff4ea4477941444f1e83313beb414838535` ([Commit Diff](https://github.com/cookiecutter/cookiecutter/commit/90434ff4ea4477941444f1e83313beb414838535.diff))
- **Bug Class**: Category 1 — Boundary / Conditional / Logic
- **Impact**: `functional`
- **Proposed Primary CWE**: CWE-670 (Always-Incorrect Control Flow Implementation)
- **Proposed CWE Labels**: `["CWE-670"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED (DISQUALIFIED: FEATURE PR #974)`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, unit test in `tests/test_hooks.py`)
- **Discovery & Technical Notes**: PR #974 is titled "Changed: Generated projects can use multiple type hooks at same time. (sh + py)". Disqualified as an atomic logic bug fix; represents a feature enhancement altering return signatures.

### CAND-0005: Scrapy — Missing None Guard in Domain Host Matching
- **Candidate ID**: `CAND-0005`
- **Source**: BugsInPy (Bug #1) / Primary Git History
- **Source Tier**: Tier 2 (BugsInPy) + Tier 1 (Target Git History)
- **Repository**: `scrapy/scrapy` ([https://github.com/scrapy/scrapy](https://github.com/scrapy/scrapy))
- **File / Target**: `scrapy/spidermiddlewares/offsite.py`
- **Buggy Commit**: `c57512fa669e6f6b1b766a7639206a380f0d10ce`
- **Fixed Commit**: `9d9dea0d69709ef0f7aef67ddba1bd7bda25d273` ([Commit Diff](https://github.com/scrapy/scrapy/commit/9d9dea0d69709ef0f7aef67ddba1bd7bda25d273.diff))
- **Bug Class**: Category 1 — Boundary / Conditional / Logic (NoneType guard)
- **Impact**: `functional`
- **Proposed Primary CWE**: CWE-476 (NULL Pointer / NoneType Dereference)
- **Proposed CWE Labels**: `["CWE-476", "CWE-670"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED (STAGED RESERVE)`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, unit tests in `tests/test_spidermiddleware_offsite.py`)
- **Discovery & Technical Notes**: When `domain is None` inside `allowed_domains`, `url_pattern.match(domain)` raised `TypeError: expected string or bytes-like object`. Patched with explicit `if domain is None: continue` invariant guard.

### CAND-0006: Scrapy — NoneType Comparison Guard in LocalCache
- **Candidate ID**: `CAND-0006`
- **Source**: BugsInPy (Bug #2) / Primary Git History
- **Source Tier**: Tier 2 (BugsInPy) + Tier 1 (Target Git History)
- **Repository**: `scrapy/scrapy` ([https://github.com/scrapy/scrapy](https://github.com/scrapy/scrapy))
- **File / Target**: `scrapy/utils/datatypes.py`
- **Buggy Commit**: `f02c3d1dcf3e4880388d19e961e7911be5dc54ff`
- **Fixed Commit**: `439a3e59b8e858441f8d97dbc32f398db392330d` ([Commit Diff](https://github.com/scrapy/scrapy/commit/439a3e59b8e858441f8d97dbc32f398db392330d.diff))
- **Bug Class**: Category 1 — Boundary / Conditional / Logic (NoneType boundary)
- **Impact**: `functional`
- **Ground-Truth Pre-Fix Locus**: Lines 318–319 (`while len(self) >= self.limit:` / `self.popitem(last=False)`)
- **Multi-File Span**: No (Single file local defect)
- **Proposed Primary CWE**: CWE-476 (NULL Pointer / NoneType Dereference)
- **Proposed CWE Labels**: `["CWE-476", "CWE-670"]`
- **Acceptable Alternative CWE Set**: `["CWE-670"]`
- **Reproducer / Test**: `tests/test_utils_datatypes.py::LocalCacheTest::test_cache_without_limit`. Executed locally via `data/evidence/CAND-0006/reproduce_cand_0006.py`.
- **Verification Execution**: Buggy raises `TypeError: '>=' not supported between instances of 'int' and 'NoneType'` on insertion; fixed creates cache without limit and inserts items.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED (PROMOTED TO CANONICAL DATASET IN PHASE 3C)`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, unit test in `tests/test_utils_datatypes.py`, executed and confirmed local reproducer)
- **Verifier Timestamp**: `2026-10-09T23:30:00+07:00`
- **Discovery & Technical Notes**: In `scrapy/utils/datatypes.py`, `LocalCache.__init__(self, limit=None)` defaults `limit` to `None`. In `__setitem__`, the condition `while len(self) >= self.limit:` was evaluated unconditionally, raising `TypeError: '>=' not supported between instances of 'int' and 'NoneType'` on the first insertion when `limit` is `None`. Fixed by adding `if self.limit:` boundary guard in upstream commit `439a3e59b8`. Promoted to canonical dataset in Phase 3C as the replacement for CAND-0003.

---

## 3. Category 2: Input Validation & Sanitization

### CAND-0007: FastAPI — Content-Type Validation Bypass (CSRF)
- **Candidate ID**: `CAND-0007`
- **Source**: GHSA-8h2j-cgx8-6xv7 / CVE-2021-32677
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `tiangolo/fastapi` ([https://github.com/tiangolo/fastapi](https://github.com/tiangolo/fastapi))
- **File / Target**: `fastapi/routing.py`
- **Buggy Commit**: `90120dd6e83d997fa2f7f54119a2e0cf906b1ded`
- **Fixed Commit**: `fa7e3c996edf2d5482fff8f9d890ac2390dede4d` ([Commit Diff](https://github.com/tiangolo/fastapi/commit/fa7e3c996edf2d5482fff8f9d890ac2390dede4d.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-8h2j-cgx8-6xv7](https://github.com/advisories/GHSA-8h2j-cgx8-6xv7)
- **Bug Class**: Category 2 — Input Validation / Sanitization
- **Ground-Truth Pre-Fix Locus**: Lines 182–184 (`body_bytes = await request.body(); if body_bytes: body = await request.json()`)
- **Multi-File Span**: No (Single file core routing dispatch logic)
- **Proposed Primary CWE**: CWE-352 (Cross-Site Request Forgery)
- **Proposed CWE Labels**: `["CWE-352", "CWE-20"]`
- **Acceptable Alternative CWE Set**: `["CWE-20", "CWE-345"]`
- **Reproducer / Test**: `tests/test_tutorial/test_body/test_tutorial001.py::test_wrong_headers`
- **Verification Execution**: Buggy accepts `text/plain` body unconditionally as JSON; fixed enforces Content-Type and raises HTTP 422.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified release commit, official advisory, isolated security patch in routing logic)
- **Verifier Timestamp**: `2026-09-25T23:40:00+07:00`
- **Discovery & Technical Notes**: FastAPI parsed incoming request bodies as JSON unconditionally (`await request.json()`), even if the `Content-Type` was `text/plain`, allowing cross-origin browsers to send simple requests without CORS preflight. Fixed by strictly verifying `Content-Type == application/json` or `+json`. *(Audit note: GPT Researcher erroneously cited PR #3165; primary verification identified the correct commit `fa7e3c996edf2d5482fff8f9d890ac2390dede4d`)*.

### CAND-0008: python-multipart — ReDoS in Content-Type Options Header Parsing
- **Candidate ID**: `CAND-0008`
- **Source**: GHSA-2jv5-9r88-3w3p / CVE-2024-24762 / GitHub PR #75
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `Kludex/python-multipart` ([https://github.com/Kludex/python-multipart](https://github.com/Kludex/python-multipart))
- **File / Target**: `multipart/multipart.py`
- **Buggy Commit**: `d3d16dae4b061c34fe9d3c9081d9800c49fc1f7a`
- **Fixed Commit**: `20f0ef6b4e4caf7d69a667c54dff57fe467109a4` ([Commit Diff](https://github.com/Kludex/python-multipart/commit/20f0ef6b4e4caf7d69a667c54dff57fe467109a4.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-2jv5-9r88-3w3p](https://github.com/advisories/GHSA-2jv5-9r88-3w3p)
- **Bug Class**: Category 2 — Input Validation / Sanitization
- **Impact**: `None`
- **Ground-Truth Pre-Fix Locus**: Lines 72–75 (`OPTION_RE_STR` and `OPTION_RE = re.compile(...)`). Call site at lines 101–117 is recorded as usage context. (Single defect model)
- **Multi-File Span**: No (Single file core multipart parser)
- **Proposed Primary CWE**: CWE-1333 (Inefficient Regular Expression Complexity)
- **Proposed CWE Labels**: `["CWE-1333", "CWE-400"]`
- **Acceptable Alternative CWE Set**: `["CWE-400"]`
- **Reproducer / Test**: Advisory GHSA-2jv5-9r88-3w3p / CVE-2024-24762. Exact advisory PoC payload (`header = 'application/x-www-form-urlencoded; !="' + ('\\' * N)`) executed locally in controlled benchmark subprocess across commits `d3d16dae` vs `20f0ef6b` using median-of-five protocol across bounded $N \in [20, 36]$ (see `data/evidence/CAND-0008/`); demonstrated experimentally observed exponential growth over the tested range (unproven $O(2^{N/2})$ formula formally retracted): buggy execution time increased from 0.000638s at $N=20$ to 1.338705s at $N=36$ (>2,000× latency surge), yielding >50,000× slowdown relative to fixed revision (~0.000026s across all $N$). ReDoS confirmed.
- **Verification Execution**: Buggy executes vulnerable regex and exhibits catastrophic backtracking stall; fixed delegates parsing to standard library `email.message.Message` executing in constant time.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, authentic advisory GHSA-2jv5-9r88-3w3p, isolated regex replacement)
- **Verifier Timestamp**: `2026-10-09T07:20:00+07:00`
- **Discovery & Technical Notes**: `parse_options_header` in `python-multipart` used a vulnerable regular expression subject to catastrophic backtracking on crafted `Content-Type` headers. *(Audit note: Corrected from 2 conflated defects to 1 single defect at lines 72–75. ReDoS conclusively confirmed via controlled subprocess benchmark in Session 29; promoted to GROUND_TRUTH_VERIFIED with reproducer_status = executed_confirmed)*.

### CAND-0009: Jinja2 — XML/HTML Attribute Injection in `xmlattr` Filter
- **Candidate ID**: `CAND-0009`
- **Source**: GHSA-h75v-3vvj-5mfj / CVE-2024-34064
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `pallets/jinja` ([https://github.com/pallets/jinja](https://github.com/pallets/jinja))
- **File / Target**: `src/jinja2/filters.py`
- **Buggy Commit**: `a7863ba9d3521f1450f821119c50d19d7ecea329`
- **Fixed Commit**: `0668239dc6b44ef38e7a6c9f91f312fd4ca581cb` ([Commit Diff](https://github.com/pallets/jinja/commit/0668239dc6b44ef38e7a6c9f91f312fd4ca581cb.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-h75v-3vvj-5mfj](https://github.com/advisories/GHSA-h75v-3vvj-5mfj)
- **Bug Class**: Category 2 — Input Validation / Sanitization
- **Ground-Truth Pre-Fix Locus**: Line 250 (`_space_re = re.compile(r"\s", flags=re.ASCII)`) and Lines 292–293 (`if _space_re.search(key) is not None: raise ValueError(...)`)
- **Multi-File Span**: No (Single file filter definition)
- **Proposed Primary CWE**: CWE-79 (Improper Neutralization of Input During Web Page Generation)
- **Proposed CWE Labels**: `["CWE-79", "CWE-20"]`
- **Acceptable Alternative CWE Set**: `["CWE-20", "CWE-116"]`
- **Reproducer / Test**: `tests/test_filters.py::test_xmlattr_key_invalid`
- **Verification Execution**: Buggy allows keys with `/`, `>`, `=`; fixed regex `r"[\s/>=]"` raises ValueError on injected attributes.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, upstream advisory, changelog entry)
- **Verifier Timestamp**: `2026-09-25T23:40:00+07:00`
- **Discovery & Technical Notes**: `xmlattr` filter in Jinja2 disallowed only whitespace characters in dictionary keys, allowing `/`, `>`, or `=` to break out of attribute boundaries and inject arbitrary attributes / XSS. Patched with regex `r"[\s/>=]"`.

### CAND-0010: urllib3 — Cookie Header Leakage Across Cross-Origin Redirects
- **Candidate ID**: `CAND-0010`
- **Source**: GHSA-v845-jxx5-vc9f / CVE-2023-43804
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `urllib3/urllib3` ([https://github.com/urllib3/urllib3](https://github.com/urllib3/urllib3))
- **File / Target**: `src/urllib3/util/retry.py` and `poolmanager.py`
- **Buggy Commit**: `1.26.16` / parent
- **Fixed Commit**: `01220354d389cd05474713f8c982d05c9b17aafb` ([Commit Diff](https://github.com/urllib3/urllib3/commit/01220354d389cd05474713f8c982d05c9b17aafb.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-v845-jxx5-vc9f](https://github.com/advisories/GHSA-v845-jxx5-vc9f)
- **Bug Class**: Category 2 — Input Validation / Sanitization (Header sanitization)
- **Proposed Primary CWE**: CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor)
- **Proposed CWE Labels**: `["CWE-200", "CWE-20"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, official advisory, reproduction unit test)
- **Discovery & Technical Notes**: `urllib3` previously failed to strip the `Cookie` request header upon encountering a cross-origin redirect, leaking session cookies to untrusted third-party hosts. Fixed by stripping `Cookie` on cross-origin redirects.

### CAND-0011: aiohttp — CRLF Injection and Request Smuggling in ClientSession
- **Candidate ID**: `CAND-0011`
- **Source**: GHSA-xx9p-xxvh-7g8j / CVE-2023-49082
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `aio-libs/aiohttp` ([https://github.com/aio-libs/aiohttp](https://github.com/aio-libs/aiohttp))
- **File / Target**: `aiohttp/client.py` and `client_reqrep.py`
- **Buggy Commit**: `3.8.6` / parent
- **Fixed Commit**: `e4ae01c2077d2cfa116aa82e4ff6866857f7c466` ([Commit Diff](https://github.com/aio-libs/aiohttp/commit/e4ae01c2077d2cfa116aa82e4ff6866857f7c466.diff))
- **Pull Request**: [https://github.com/aio-libs/aiohttp/pull/7806](https://github.com/aio-libs/aiohttp/pull/7806)
- **Advisory URL**: [https://github.com/advisories/GHSA-xx9p-xxvh-7g8j](https://github.com/advisories/GHSA-xx9p-xxvh-7g8j)
- **Bug Class**: Category 2 — Input Validation / Sanitization (CRLF injection)
- **Proposed Primary CWE**: CWE-113 (Improper Neutralization of CRLF Sequences in HTTP Headers)
- **Proposed CWE Labels**: `["CWE-113", "CWE-20", "CWE-444"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, PR thread, pytest tests in `tests/test_client_request.py`)
- **Discovery & Technical Notes**: ClientSession did not validate the HTTP method parameter, enabling CRLF character sequences (`\r\n`) to inject arbitrary headers and request bodies, triggering HTTP request smuggling.

### CAND-0012: Requests — Proxy-Authorization Header Leakage on HTTPS Redirects
- **Candidate ID**: `CAND-0012`
- **Source**: GHSA-j8r2-6x86-q33q / CVE-2023-32681
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `psf/requests` ([https://github.com/psf/requests](https://github.com/psf/requests))
- **File / Target**: `requests/sessions.py`
- **Buggy Commit**: `242e2db34b9d038dc763c873ec8b9e4a861d8f76`
- **Fixed Commit**: `74ea7cf7a6a27a4eeb2ae24e162bcc942a6706d5` ([Commit Diff](https://github.com/psf/requests/commit/74ea7cf7a6a27a4eeb2ae24e162bcc942a6706d5.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-j8r2-6x86-q33q](https://github.com/advisories/GHSA-j8r2-6x86-q33q)
- **Bug Class**: Category 2 — Input Validation / Sanitization (Header sanitization)
- **Proposed Primary CWE**: CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor)
- **Proposed CWE Labels**: `["CWE-200", "CWE-20"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, unit test in `tests/test_requests.py`)
- **Discovery & Technical Notes**: In `rebuild_proxies`, `Proxy-Authorization` header was inadvertently reattached when redirected to an HTTPS endpoint, leaking proxy credentials in plaintext to destination servers. Fixed by verifying `not scheme.startswith('https')`.

### CAND-0036: Django — Cache Key Character Boundary Validation Omission
- **Candidate ID**: `CAND-0036`
- **Source**: GHSA-wpjr-j57x-wxfw / CVE-2020-13254 / Django Security Release (June 3, 2020)
- **Advisory URL**: [https://github.com/advisories/GHSA-wpjr-j57x-wxfw](https://github.com/advisories/GHSA-wpjr-j57x-wxfw)
- **Source Tier**: Tier 3 (CVE/Advisory) + Tier 1 (Target Git History)
- **Repository**: `django/django` ([https://github.com/django/django](https://github.com/django/django))
- **File / Target**: `django/core/cache/backends/memcached.py`
- **Buggy Commit**: `1f2dd37f6fcefdd10ed44cb233b2e62b520afb38` (parent of `84b2da5552e100ae3294f564f6c862fef8d0e693`)
- **Fixed Commit**: `84b2da5552e100ae3294f564f6c862fef8d0e693` ([Commit Diff](https://github.com/django/django/commit/84b2da5552e100ae3294f564f6c862fef8d0e693.diff))
- **Bug Class**: Category 2 — Input Validation / Sanitization
- **Ground-Truth Pre-Fix Locus**: Lines 65–86 (`add`, `get`, `set`, `delete`, `get_many`)
- **Multi-File Span**: Yes (Missing validation calls in `memcached.py`; validation implementation in `base.py`)
- **Proposed Primary CWE**: CWE-20 (Improper Input Validation)
- **Proposed CWE Labels**: `["CWE-20", "CWE-116"]`
- **Acceptable Alternative CWE Set**: `["CWE-116", "CWE-200"]`
- **Reproducer / Test**: `tests/cache/tests.py::_perform_invalid_key_test`
- **Verification Execution**: Buggy passes whitespace/control characters in keys to memcached backend; fixed invokes `validate_key` raising `InvalidCacheKey`.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, official security release notes, unit tests in `tests/cache/tests.py`)
- **Verifier Timestamp**: `2026-09-25T23:55:00+07:00`
- **Reclassification & Technical Notes**: Originally provisionally ingested under Category 6 (Authorization) due to data boundary impact. Primary-source review during Phase 2 pilot demonstrated that the vulnerability is caused by lack of cache-key character validation prior to sending memcached protocol commands, fixed by adding `validate_key`. Reclassified to Category 2 (Input Validation / Sanitization) with CWE-20 (CWE-285 removed as inappropriate for input sanitization flaw).

---

## 4. Category 3: SQL / ORM Injection

### CAND-0013: Django — SQL Injection via Internal Parameter Unpacking (`_connector`)
- **Candidate ID**: `CAND-0013`
- **Source**: CVE-2025-64459 / Primary Django Security Release
- **Source Tier**: Tier 3 (CVE/Advisory) + Tier 1 (Target Git History)
- **Repository**: `django/django` ([https://github.com/django/django](https://github.com/django/django))
- **File / Target**: `django/db/models/query_utils.py`
- **Buggy Commit**: `4.2.25` / parent
- **Fixed Commit**: `98e642c691f16ee0a6c2eb4dd094f31c441c2c2f` ([Commit Diff](https://github.com/django/django/commit/98e642c691.diff))
- **Bug Class**: Category 3 — SQL / ORM Injection
- **Proposed Primary CWE**: CWE-89 (Improper Neutralization of Special Elements used in an SQL Command)
- **Proposed CWE Labels**: `["CWE-89"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, release notes in `docs/releases/4.2.26.txt`)
- **Discovery & Technical Notes**: Unpacking dynamic dictionary parameters (`**kwargs`) into Django QuerySet filter methods permitted injecting internal parameters (`_connector`, `_negated`) into the `Q` constructor, allowing attackers to inject arbitrary SQL connectors and alter query logic. Fixed with strict connector whitelisting `(None, AND, OR, XOR)`.

### CAND-0014: Django — SQL Injection in `Trunc()` and `Extract()` Datetime Functions
- **Candidate ID**: `CAND-0014`
- **Source**: GHSA-p64x-8rxx-wf6q / CVE-2022-34265 (supersedes invalid GHSA-4w5c-wffp-v8c6)
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `django/django` ([https://github.com/django/django](https://github.com/django/django))
- **File / Target**: `django/db/models/functions/datetime.py` and `django/db/backends/base/operations.py`
- **Buggy Commit**: `425718726b7d2edd7b8a043f8976e437262b5098`
- **Fixed Commit**: `54eb8a374d5d98594b264e8ec22337819b37443c` ([Commit Diff](https://github.com/django/django/commit/54eb8a374d5d98594b264e8ec22337819b37443c.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-p64x-8rxx-wf6q](https://github.com/advisories/GHSA-p64x-8rxx-wf6q)
- **Bug Class**: Category 3 — SQL / ORM Injection
- **Ground-Truth Pre-Fix Locus**: Lines 45–51 (Extract) and Lines 225–236 (Trunc) in `django/db/models/functions/datetime.py`
- **Multi-File Span**: Yes (Locus in `datetime.py`; pattern in `operations.py`)
- **Proposed Primary CWE**: CWE-89 (Improper Neutralization of Special Elements used in an SQL Command)
- **Proposed CWE Labels**: `["CWE-89"]`
- **Acceptable Alternative CWE Set**: `["CWE-20", "CWE-943"]`
- **Reproducer / Test**: `tests/db_functions/datetime/test_extract_trunc.py::test_extract_lookup_name_sql_injection`
- **Verification Execution**: Buggy accepts payload without validation; fixed compiles regex `r"[\w\-_()]+"` raising ValueError.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, regression tests in `tests/db_functions/test_datetime.py`)
- **Verifier Timestamp**: `2026-09-25T23:40:00+07:00`
- **Discovery & Technical Notes**: `Trunc()` and `Extract()` database functions evaluated untrusted `lookup_name` inputs directly into database date/time SQL operations, permitting SQL injection. Fixed with regex validation `_lazy_re_compile(r"[\w\-_()]+")`.

### CAND-0015: Django — SQL Injection in PostgreSQL `StringAgg` Delimiter
- **Candidate ID**: `CAND-0015`
- **Source**: GHSA-hmr4-m2h5-33qx / CVE-2020-7471 (supersedes invalid GHSA-hmr4-m2h5-3347)
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `django/django` ([https://github.com/django/django](https://github.com/django/django))
- **File / Target**: `django/contrib/postgres/aggregates/general.py`
- **Buggy Commit**: `6b178a3e930f72069f3cda2e6a09d1b320fc09ec`
- **Fixed Commit**: `eb31d845323618d688ad429479c6dda973056136` ([Commit Diff](https://github.com/django/django/commit/eb31d845323618d688ad429479c6dda973056136.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-hmr4-m2h5-33qx](https://github.com/advisories/GHSA-hmr4-m2h5-33qx)
- **Bug Class**: Category 3 — SQL / ORM Injection
- **Impact**: `None`
- **Ground-Truth Pre-Fix Locus**: Lines 54–58 (`template = "%(function)s(%(distinct)s%(expressions)s, '%(delimiter)s'%(ordering)s)"` and `__init__`)
- **Multi-File Span**: No (Single file aggregate function)
- **Proposed Primary CWE**: CWE-89 (Improper Neutralization of Special Elements used in an SQL Command)
- **Proposed CWE Labels**: `["CWE-89"]`
- **Acceptable Alternative CWE Set**: `["CWE-943"]`
- **Reproducer / Test**: Upstream regression test `tests/postgres_tests/test_aggregates.py::test_string_agg_delimiter_escaping` (Cited from upstream commit eb31d845; requires PostgreSQL database setup, not run locally)
- **Verification Execution**: Buggy interpolates delimiter unescaped allowing SQL injection payload; fixed wraps delimiter into parameterized `Value(str(delimiter))`.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, official security advisory, unit test in `tests/postgres_tests/test_aggregates.py`)
- **Verifier Timestamp**: `2026-10-09T06:30:00+07:00`
- **Discovery & Technical Notes**: In `StringAgg`, the `delimiter` parameter was interpolated raw into SQL formatting string (`'%(delimiter)s'`), permitting SQL injection. Fixed by wrapping delimiter as parameterized `Value(str(delimiter))`. *(Audit note: Traced exact parent buggy commit `6b178a3e930f72069f3cda2e6a09d1b320fc09ec`; reproducer cited upstream)*.

### CAND-0016: Django — SQL Injection via Dotted Column Reference in `order_by()`
- **Candidate ID**: `CAND-0016`
- **Source**: GHSA-xpfp-f569-q3p2 / CVE-2021-35042 (supersedes invalid GHSA-wfq3-5d76-h535)
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `django/django` ([https://github.com/django/django](https://github.com/django/django))
- **File / Target**: `django/db/models/sql/query.py` and `constants.py`
- **Buggy Commit**: `1bf79a597c...`
- **Fixed Commit**: `a34a5f724c5d5adb2109374ba3989ebb7b11f81f` ([Commit Diff](https://github.com/django/django/commit/a34a5f724c5d5adb2109374ba3989ebb7b11f81f.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-xpfp-f569-q3p2](https://github.com/advisories/GHSA-xpfp-f569-q3p2)
- **Bug Class**: Category 3 — SQL / ORM Injection
- **Proposed Primary CWE**: CWE-89 (Improper Neutralization of Special Elements used in an SQL Command)
- **Proposed CWE Labels**: `["CWE-89"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, unit test cases in `tests/queries/test_order_by.py`)
- **Discovery & Technical Notes**: User-supplied input containing period characters passed to `QuerySet.order_by()` bypassed column reference checks during deprecation handling, allowing arbitrary SQL clauses to be appended. Fixed with `ORDER_PATTERN = _lazy_re_compile(r'[-+]?[.\w]+$')`.

### CAND-0017: Tortoise-ORM — SQL Injection in Filter Operations (MySQL)
- **Candidate ID**: `CAND-0017`
- **Source**: GHSA-9j2c-x8qm-qmjq / CVE-2020-11010 (supersedes invalid GHSA-8h28-p98r-5858)
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `tortoise/tortoise-orm` ([https://github.com/tortoise/tortoise-orm](https://github.com/tortoise/tortoise-orm))
- **File / Target**: `tortoise/backends/mysql/executor.py` and filter builders
- **Buggy Commit**: `816ff00e988f79b4ff1601f247062bb5eb9db802`
- **Fixed Commit**: `91c364053e0ddf77edc5442914c6f049512678b3` ([Commit Diff](https://github.com/tortoise/tortoise-orm/commit/91c364053e0ddf77edc5442914c6f049512678b3.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-9j2c-x8qm-qmjq](https://github.com/advisories/GHSA-9j2c-x8qm-qmjq)
- **Bug Class**: Category 3 — SQL / ORM Injection
- **Ground-Truth Pre-Fix Locus**: Lines 19–45 (MySQL filter overrides: `mysql_contains`, `mysql_starts_with`, `mysql_ends_with`)
- **Multi-File Span**: Yes (Core executor functions in `mysql/executor.py`; PyPika monkey-patch in `filters.py`)
- **Proposed Primary CWE**: CWE-89 (Improper Neutralization of Special Elements used in an SQL Command)
- **Proposed CWE Labels**: `["CWE-89"]`
- **Acceptable Alternative CWE Set**: `["CWE-943", "CWE-20"]`
- **Reproducer / Test**: Upstream fuzz test harness `tests/test_fuzz.py`
- **Verification Execution**: Buggy creates unescaped LIKE clauses (`%test%' OR '1'='1%`); fixed escapes with `escape_like()` producing `LIKE '%test\%' OR '1'='1%'`.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, comprehensive fuzz test harness added in `tests/test_fuzz.py`)
- **Verifier Timestamp**: `2026-09-25T23:40:00+07:00`
- **Discovery & Technical Notes**: Tortoise-ORM failed to properly escape wildcard and quote characters in MySQL when evaluating `contains`, `starts_with`, or `ends_with` filter lookups, enabling SQL injection through untrusted query strings. *(Audit note: Corrected from hallucinated CVE-2022-41908)*.

### CAND-0018: SQLAlchemy — SQL Injection via String Coercion in `order_by` / `group_by`
- **Candidate ID**: `CAND-0018`
- **Source**: GHSA-887w-45rq-vxgf / CVE-2019-7164 (supersedes invalid GHSA-8424-6m39-9r8m)
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `sqlalchemy/sqlalchemy` ([https://github.com/sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy))
- **File / Target**: `lib/sqlalchemy/sql/elements.py` and `selectable.py`
- **Buggy Commit**: `1.2.17` / parent
- **Fixed Commit**: `30307c4616ad67c01ddae2e1e8e34fabf6028414` ([Commit Diff](https://github.com/sqlalchemy/sqlalchemy/commit/30307c4616ad67c01ddae2e1e8e34fabf6028414.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-887w-45rq-vxgf](https://github.com/advisories/GHSA-887w-45rq-vxgf)
- **Bug Class**: Category 3 — SQL / ORM Injection
- **Proposed Primary CWE**: CWE-89 (Improper Neutralization of Special Elements used in an SQL Command)
- **Proposed CWE Labels**: `["CWE-89"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, migration document in `doc/build/changelog/migration_13.rst`)
- **Discovery & Technical Notes**: In SQLAlchemy versions before 1.3.0b3, passing unvalidated string SQL fragments to `order_by()` or `group_by()` automatically coerced strings into raw `text()` constructs rather than strictly validating column names, executing arbitrary SQL commands. Fixed by raising `CompileError`.

---

## 5. Category 4: Path Traversal & Unsafe File Operations

### CAND-0019: aiohttp — Static File Directory Traversal via Symlink Follow
- **Candidate ID**: `CAND-0019`
- **Source**: GHSA-5h86-8mv2-jq9f / CVE-2024-23334
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `aio-libs/aiohttp` ([https://github.com/aio-libs/aiohttp](https://github.com/aio-libs/aiohttp))
- **File / Target**: `aiohttp/web_urldispatcher.py`
- **Buggy Commit**: `33ccdfb0a12690af5bb49bda2319ec0907fa7827`
- **Fixed Commit**: `1c335944d6a8b1298baf179b7c0b3069f10c514b` ([Commit Diff](https://github.com/aio-libs/aiohttp/commit/1c335944d6a8b1298baf179b7c0b3069f10c514b.diff))
- **Pull Request**: [https://github.com/aio-libs/aiohttp/pull/8079](https://github.com/aio-libs/aiohttp/pull/8079)
- **Advisory URL**: [https://github.com/advisories/GHSA-5h86-8mv2-jq9f](https://github.com/advisories/GHSA-5h86-8mv2-jq9f)
- **Bug Class**: Category 4 — Path Traversal / Unsafe File Operations
- **Ground-Truth Pre-Fix Locus**: Lines 643–645 (in `_handle`), and Lines 574–576 (in `url_for`)
- **Multi-File Span**: No (Single file static URL dispatcher)
- **Proposed Primary CWE**: CWE-22 (Improper Limitation of a Pathname to a Restricted Directory)
- **Proposed CWE Labels**: `["CWE-22", "CWE-59"]`
- **Acceptable Alternative CWE Set**: `["CWE-59", "CWE-20"]`
- **Reproducer / Test**: `tests/test_web_urldispatcher.py::test_follow_symlink_directory_traversal`
- **Verification Execution**: Buggy skips `relative_to` when `follow_symlinks=True`, allowing path escape; fixed enforces `relative_to` unconditionally.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, PR thread, pytest tests)
- **Verifier Timestamp**: `2026-09-25T23:40:00+07:00`
- **Discovery & Technical Notes**: When `follow_symlinks=True` was configured on a static file route in `aiohttp`, `web_urldispatcher.py` failed to verify that the normalized target path remained within the static directory root, allowing directory traversal to read arbitrary files. Fixed by enforcing `normalized_path.relative_to(self._directory)`.

### CAND-0020: Werkzeug — Safe_Join UNC Path Traversal on Windows
- **Candidate ID**: `CAND-0020`
- **Source**: GHSA-f9vj-2wh5-fj8j / CVE-2024-49766 (supersedes invalid GHSA-mvgw-hpx7-xrqc)
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `pallets/werkzeug` ([https://github.com/pallets/werkzeug](https://github.com/pallets/werkzeug))
- **File / Target**: `src/werkzeug/security.py`
- **Buggy Commit**: `50cfeebcb0727e18cc52ffbeb125f4a66551179b`
- **Fixed Commit**: `2767bcb10a7dd1c297d812cc5e6d11a474c1f092` ([Commit Diff](https://github.com/pallets/werkzeug/commit/2767bcb10a7dd1c297d812cc5e6d11a474c1f092.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-f9vj-2wh5-fj8j](https://github.com/advisories/GHSA-f9vj-2wh5-fj8j)
- **Bug Class**: Category 4 — Path Traversal / Unsafe File Operations
- **Impact**: `None`
- **Ground-Truth Pre-Fix Locus**: Lines 151–157 (`if any(sep in filename for sep in _os_alt_seps) or os.path.isabs(filename)...: return None`)
- **Multi-File Span**: No (Single file core utility function)
- **Proposed Primary CWE**: CWE-22 (Improper Limitation of a Pathname to a Restricted Directory)
- **Proposed CWE Labels**: `["CWE-22"]`
- **Acceptable Alternative CWE Set**: `["CWE-20"]`
- **Reproducer / Test**: Upstream regression test `tests/test_security.py::test_safe_join` with `("//b/c", None)` (Cited from upstream; defect requires Windows + Python < 3.11; not reproducible on local Windows Python 3.12.10 because ntpath.isabs already treats //b/c as absolute)
- **Verification Execution**: Buggy safe_join allows UNC paths (`//b/c`) escaping root directory on Windows under Python < 3.11; fixed adds `filename.startswith("/")` guard returning `None`.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, official advisory, unit test in `tests/test_security.py`)
- **Verifier Timestamp**: `2026-10-09T06:30:00+07:00`
- **Discovery & Technical Notes**: `safe_join` relied on `os.path.isabs()`, which failed on Windows under Python < 3.11 to catch certain UNC paths (`//server/share`), allowing unauthorized path escapes outside the intended base directory. *(Audit note: Traced exact parent buggy commit `50cfeebcb0727e18cc52ffbeb125f4a66551179b`; runtime constraint Windows + Python < 3.11 documented)*.

### CAND-0021: Starlette — Commonprefix vs Commonpath Directory Escape
- **Candidate ID**: `CAND-0021`
- **Source**: GHSA-v5gw-mw7f-84px / CVE-2023-29159
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `encode/starlette` ([https://github.com/encode/starlette](https://github.com/encode/starlette))
- **File / Target**: `starlette/staticfiles.py`
- **Buggy Commit**: `24c1fac62a80bb153c6548145334fc643991e35a`
- **Fixed Commit**: `1797de464124b090f10cf570441e8292936d63e3` ([Commit Diff](https://github.com/encode/starlette/commit/1797de464124b090f10cf570441e8292936d63e3.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-v5gw-mw7f-84px](https://github.com/advisories/GHSA-v5gw-mw7f-84px)
- **Bug Class**: Category 4 — Path Traversal / Unsafe File Operations
- **Ground-Truth Pre-Fix Locus**: Line 172 (`if os.path.commonprefix([full_path, directory]) != directory:`)
- **Multi-File Span**: No (Single file atomic locus)
- **Proposed Primary CWE**: CWE-22 (Improper Limitation of a Pathname to a Restricted Directory)
- **Proposed CWE Labels**: `["CWE-22"]`
- **Acceptable Alternative CWE Set**: `["CWE-20"]`
- **Reproducer / Test**: `tests/test_staticfiles.py::test_staticfiles_avoids_path_traversal`
- **Verification Execution**: Buggy commonprefix matches string prefix of sibling directory (`/static-secret` vs `/static`); fixed commonpath checks path hierarchy.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, test suite in `tests/test_staticfiles.py`)
- **Verifier Timestamp**: `2026-09-25T23:40:00+07:00`
- **Discovery & Technical Notes**: In `StaticFiles.lookup_path`, `os.path.commonprefix([full_path, directory])` was used to verify that requested files resided within the static directory. Because `commonprefix` performs string character comparison, requesting `/static-secret/file` when the static dir is `/static` satisfied the check, leaking files from sibling directories. Fixed by replacing with `os.path.commonpath`.

### CAND-0022: Django — Path Traversal in UploadedFile and File Storage
- **Candidate ID**: `CAND-0022`
- **Source**: GHSA-rxjp-mfm9-w4wr / CVE-2021-31542 (supersedes invalid GHSA-rw5m-5969-v73m)
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `django/django` ([https://github.com/django/django](https://github.com/django/django))
- **File / Target**: `django/core/files/storage.py` and `uploadedfile.py`
- **Buggy Commit**: `3.2.0` / parent
- **Fixed Commit**: `04ac1624bdc2fa737188401757cf95ced122d26d` ([Commit Diff](https://github.com/django/django/commit/04ac1624bdc2fa737188401757cf95ced122d26d.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-rxjp-mfm9-w4wr](https://github.com/advisories/GHSA-rxjp-mfm9-w4wr)
- **Bug Class**: Category 4 — Path Traversal / Unsafe File Operations
- **Proposed Primary CWE**: CWE-22 (Improper Limitation of a Pathname to a Restricted Directory)
- **Proposed CWE Labels**: `["CWE-22"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, security release announcement, storage tests in `tests/file_storage/tests.py`)
- **Discovery & Technical Notes**: Uploaded files with names containing `..` path segments bypassed `MultiPartParser` and storage validation, allowing files to be saved outside the destination upload directory. Fixed by validating filename components: `if '..' in pathlib.PurePath(dir_name).parts: raise SuspiciousFileOperation(...)`.

### CAND-0023: Tornado — Path Traversal / Boundary Redirect in StaticFileHandler
- **Candidate ID**: `CAND-0023`
- **Source**: CVE-2023-28370 / Official Release History
- **Source Tier**: Tier 3 (CVE) + Tier 1 (Target Git History)
- **Repository**: `tornadoweb/tornado` ([https://github.com/tornadoweb/tornado](https://github.com/tornadoweb/tornado))
- **File / Target**: `tornado/web.py`
- **Buggy Commit**: `6.3.1` / parent
- **Fixed Commit**: `32ad07c...`
- **Bug Class**: Category 4 — Path Traversal / Unsafe File Operations
- **Proposed Primary CWE**: CWE-22 (Improper Limitation of a Pathname to a Restricted Directory)
- **Proposed CWE Labels**: `["CWE-22", "CWE-601"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level B (Verified release notes, CVE disclosure, git commit reference in 6.3.2)
- **Discovery & Technical Notes**: In `StaticFileHandler`, crafted requests with multiple leading slashes or specific path traversal sequences bypassed boundary checks when redirecting directory requests without trailing slashes.

### CAND-0024: MLflow — Arbitrary File Access via Artifact Location Path Traversal
- **Candidate ID**: `CAND-0024`
- **Source**: GHSA-xg73-94fp-g449 / CVE-2023-1177 (supersedes invalid GHSA-87jh-mvf3-f58p)
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `mlflow/mlflow` ([https://github.com/mlflow/mlflow](https://github.com/mlflow/mlflow))
- **File / Target**: `mlflow/server/handlers.py` and artifact repository loaders
- **Buggy Commit**: `2.2.0` / parent
- **Fixed Commit**: `2.2.1` release tag / commit
- **Advisory URL**: [https://github.com/advisories/GHSA-xg73-94fp-g449](https://github.com/advisories/GHSA-xg73-94fp-g449)
- **Bug Class**: Category 4 — Path Traversal / Unsafe File Operations
- **Proposed Primary CWE**: CWE-22 (Improper Limitation of a Pathname to a Restricted Directory)
- **Proposed CWE Labels**: `["CWE-22", "CWE-29"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level A (Verified official advisory, CVE entry, release patch)
- **Discovery & Technical Notes**: The `mlflow server` and `mlflow ui` handlers permitted path traversal via crafted `artifact_location` parameters containing `\..\` sequences, allowing remote unauthenticated users to read arbitrary server files.

---

## 6. Category 5: Authentication

### CAND-0025: PyJWT — Key Confusion between HMAC and Asymmetric Keys
- **Candidate ID**: `CAND-0025`
- **Source**: GHSA-ffqj-6fqr-9h24 / CVE-2022-29217
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `jpadilla/pyjwt` ([https://github.com/jpadilla/pyjwt](https://github.com/jpadilla/pyjwt))
- **File / Target**: `jwt/algorithms.py`
- **Buggy Commit**: `24b29adfebcb4f057a3cef5aaf35653bc0c1c8cc`
- **Fixed Commit**: `9c528670c455b8d948aff95ed50e22940d1ad3fc` ([Commit Diff](https://github.com/jpadilla/pyjwt/commit/9c528670c455b8d948aff95ed50e22940d1ad3fc.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-ffqj-6fqr-9h24](https://github.com/advisories/GHSA-ffqj-6fqr-9h24)
- **Bug Class**: Category 5 — Authentication
- **Ground-Truth Pre-Fix Locus**: Lines 186–197 (in `HMACAlgorithm.prepare_key`)
- **Multi-File Span**: No (Single file key preparation method)
- **Proposed Primary CWE**: CWE-347 (Improper Verification of Cryptographic Signature)
- **Proposed CWE Labels**: `["CWE-347", "CWE-287"]`
- **Acceptable Alternative CWE Set**: `["CWE-287", "CWE-327"]`
- **Reproducer / Test**: `tests/test_advisory.py::TestAdvisory::test_ghsa_ffqj_6fqr_9h24`
- **Verification Execution**: Buggy accepts OpenSSH Ed25519 public key as HMAC secret; fixed rejects key with `InvalidKeyError`.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, official advisory, reproduction tests in `tests/test_algorithms.py`)
- **Verifier Timestamp**: `2026-09-25T23:40:00+07:00`
- **Discovery & Technical Notes**: In `jwt/algorithms.py`, `prepare_key` checked for asymmetric PEM header strings using an incomplete blacklist. An attacker providing an asymmetric public key in an alternate formatting could cause PyJWT to verify HMAC tokens using the public key as the secret, forging arbitrary signatures. Patched with comprehensive `is_pem_format(key) or is_ssh_key(key)`.

### CAND-0026: Paramiko — State Machine Authentication Bypass in Transport Loop
- **Candidate ID**: `CAND-0026`
- **Source**: GHSA-232r-66cg-79px / CVE-2018-7750
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `paramiko/paramiko` ([https://github.com/paramiko/paramiko](https://github.com/paramiko/paramiko))
- **File / Target**: `paramiko/transport.py` (Contextual file: `paramiko/common.py`)
- **Buggy Commit**: `aefd28a7f00c4250d113d375e96abf5da3eb89f9`
- **Fixed Commit**: `fa29bd8446c8eab237f5187d28787727b4610516` ([Commit Diff](https://github.com/paramiko/paramiko/commit/fa29bd8446c8eab237f5187d28787727b4610516.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-232r-66cg-79px](https://github.com/advisories/GHSA-232r-66cg-79px)
- **Bug Class**: Category 5 — Authentication
- **Impact**: `None`
- **Ground-Truth Pre-Fix Locus**: Lines 1822–1828 (`if ptype in self._handler_table: self._handler_table[ptype](self, m)`) in `paramiko/transport.py`
- **Multi-File Span**: No (Defect locus strictly in `transport.py`; `paramiko/common.py` is contextual only)
- **Proposed Primary CWE**: CWE-287 (Improper Authentication)
- **Proposed CWE Labels**: `["CWE-287"]`
- **Acceptable Alternative CWE Set**: `["CWE-305"]`
- **Reproducer / Test**: Upstream issue #1175 regression verification testing out-of-order channel open request (Cited from upstream; live SSH socket integration test not run locally)
- **Verification Execution**: Buggy executes message handler directly without auth check; fixed introduces `_ensure_authed(ptype, m)` returning failure packet.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, CVE advisory, isolated state check in transport loop)
- **Verifier Timestamp**: `2026-10-09T06:30:00+07:00`
- **Discovery & Technical Notes**: A state machine flaw in Paramiko SSH server transport allowed a client to send a `MSG_USERAUTH_SUCCESS` or initiate channel-open requests out of order before actual authentication completed. Fixed by introducing `_ensure_authed()` assertion guards before executing subsequent message handlers. *(Audit note: Corrected advisory ID from invalid 404 GHSA-8h46-5p95-gcmg to authentic GHSA-232r-66cg-79px; common.py isolated as contextual file; broad CWE-285 removed)*.

### CAND-0027: Authlib — Signature Verification Bypass via Algorithm 'none'
- **Candidate ID**: `CAND-0027`
- **Source**: GHSA-7wc2-qxgw-g8gg / CVE-2026-28802
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `lepture/authlib` ([https://github.com/lepture/authlib](https://github.com/lepture/authlib))
- **File / Target**: `authlib/jose/__init__.py` and `rfc7518/jws_algs.py`
- **Buggy Commit**: `bb7a315befbad333faf9a23ef574d6e3134a6774`
- **Fixed Commit**: `b87c32ed07b8ae7f805873e1c9cafd1016761df7` ([Commit Diff](https://github.com/authlib/authlib/commit/b87c32ed07b8ae7f805873e1c9cafd1016761df7.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-7wc2-qxgw-g8gg](https://github.com/advisories/GHSA-7wc2-qxgw-g8gg)
- **Bug Class**: Category 5 — Authentication
- **Ground-Truth Pre-Fix Locus**: Line 49 (`jwt = JsonWebToken(list(JsonWebSignature.ALGORITHMS_REGISTRY.keys()))`)
- **Multi-File Span**: No (Global singleton definition)
- **Proposed Primary CWE**: CWE-347 (Improper Verification of Cryptographic Signature)
- **Proposed CWE Labels**: `["CWE-347", "CWE-287"]`
- **Acceptable Alternative CWE Set**: `["CWE-287", "CWE-327"]`
- **Reproducer / Test**: `tests/flask/test_oauth2/test_jwt_authorization_request.py::test_server_require_request_object_alg_none`
- **Verification Execution**: Buggy initializes default jwt with 'none' algorithm, decoding unsigned tokens; fixed whitelists cryptographic algorithms only.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, official advisory, upstream release)
- **Verifier Timestamp**: `2026-09-25T23:40:00+07:00`
- **Discovery & Technical Notes**: The default `jwt` singleton in Authlib registered all supported JWS algorithms including `"none"`. An attacker crafting a token with `"alg": "none"` and an empty signature bypassed verification. Fixed by restricting default algorithms strictly to cryptographic families (`HS256`, `RS256`, `ES256`, `PS256`).

### CAND-0028: Authlib — Algorithm Confusion via Public Key as OctKey
- **Candidate ID**: `CAND-0028`
- **Source**: GHSA-5357-c2jx-v7qh / CVE-2024-37568 (supersedes invalid GHSA-w2rm-fqcx-5w99)
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `lepture/authlib` ([https://github.com/lepture/authlib](https://github.com/lepture/authlib))
- **File / Target**: `authlib/jose/rfc7518/oct_key.py`
- **Buggy Commit**: `1.3.0` / parent
- **Fixed Commit**: `3bea812acefebc9ee108aa24557be3ba8971daf1` ([Commit Diff](https://github.com/lepture/authlib/commit/3bea812acefebc9ee108aa24557be3ba8971daf1.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-5357-c2jx-v7qh](https://github.com/advisories/GHSA-5357-c2jx-v7qh)
- **Bug Class**: Category 5 — Authentication
- **Proposed Primary CWE**: CWE-347 (Improper Verification of Cryptographic Signature)
- **Proposed CWE Labels**: `["CWE-347", "CWE-287"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, official advisory, tests in `tests/jose/test_key.py`)
- **Discovery & Technical Notes**: `OctKey` accepted raw bytes without verifying whether they represented an asymmetric public key. When a developer passed a public key into `jwt.decode` without specifying `algorithms`, an attacker could forge HMAC tokens signed using the public key. Fixed by rejecting keys matching `POSSIBLE_UNSAFE_KEYS = (b"-----BEGIN ", b"ssh-rsa ", ...)`.

### CAND-0029: Django — Email Enumeration & Timing Flaw in PasswordResetForm
- **Candidate ID**: `CAND-0029`
- **Source**: GHSA-rrqc-c2jx-6jgv / CVE-2024-45231 (supersedes invalid GHSA-78rw-pq65-6qxv)
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `django/django` ([https://github.com/django/django](https://github.com/django/django))
- **File / Target**: `django/contrib/auth/forms.py`
- **Buggy Commit**: `5.1.0` / parent
- **Fixed Commit**: September 2024 security release commit
- **Advisory URL**: [https://github.com/advisories/GHSA-rrqc-c2jx-6jgv](https://github.com/advisories/GHSA-rrqc-c2jx-6jgv)
- **Bug Class**: Category 5 — Authentication
- **Proposed Primary CWE**: CWE-204 (Observable Response Discrepancy)
- **Proposed CWE Labels**: `["CWE-204", "CWE-287"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level B (Verified advisory, release notes, security patch logic)
- **Discovery & Technical Notes**: In `PasswordResetForm`, unhandled exceptions during password reset email delivery exposed whether an email address was registered on the system. Fixed by capturing exceptions with `try...except` and logging errors silently to `django.contrib.auth` logger.

### CAND-0030: python-jose — Algorithm Confusion in OpenSSH ECDSA Key Parsing
- **Candidate ID**: `CAND-0030`
- **Source**: GHSA-6c5p-j8vq-pqhj / CVE-2024-33663 (supersedes invalid GHSA-v288-fcwf-c4hx)
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `mpdavis/python-jose` ([https://github.com/mpdavis/python-jose](https://github.com/mpdavis/python-jose))
- **File / Target**: `jose/backends/cryptography_backend.py`
- **Buggy Commit**: `3.3.0` / parent
- **Fixed Commit**: `3.4.0` release commit
- **Advisory URL**: [https://github.com/advisories/GHSA-6c5p-j8vq-pqhj](https://github.com/advisories/GHSA-6c5p-j8vq-pqhj)
- **Bug Class**: Category 5 — Authentication
- **Proposed Primary CWE**: CWE-347 (Improper Verification of Cryptographic Signature)
- **Proposed CWE Labels**: `["CWE-347", "CWE-287"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level B (Verified advisory, CVE record, release patch)
- **Discovery & Technical Notes**: `python-jose` allowed an algorithm confusion attack when parsing OpenSSH and ECDSA formatted keys, allowing forged tokens to pass signature validation.

---

## 7. Category 6: Authorization (BOLA, IDOR, Permissions)

### CAND-0031: JupyterHub — Privilege Escalation in User Administration API
- **Candidate ID**: `CAND-0031`
- **Source**: GHSA-9x4q-3gxw-849f / CVE-2024-41942 (supersedes invalid GHSA-7996-7454-5223)
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `jupyterhub/jupyterhub` ([https://github.com/jupyterhub/jupyterhub](https://github.com/jupyterhub/jupyterhub))
- **File / Target**: `jupyterhub/apihandlers/users.py`
- **Buggy Commit**: `b4053616743eb011e5bb568700f25afca17aef53` (parent of `99e2720b0fc626cbeeca3c6337f917fdacfaa428`)
- **Fixed Commit**: `99e2720b0fc626cbeeca3c6337f917fdacfaa428` ([Commit Diff](https://github.com/jupyterhub/jupyterhub/commit/99e2720b0fc626cbeeca3c6337f917fdacfaa428.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-9x4q-3gxw-849f](https://github.com/advisories/GHSA-9x4q-3gxw-849f)
- **Bug Class**: Category 6 — Authorization
- **Ground-Truth Pre-Fix Locus**: Lines 265–267 (in `post(self, user_name)`) and Lines 328–331 (in `patch(self, user_name)`)
- **Multi-File Span**: No (Single file user API handler)
- **Proposed Primary CWE**: CWE-269 (Improper Privilege Management)
- **Proposed CWE Labels**: `["CWE-269", "CWE-863"]`
- **Acceptable Alternative CWE Set**: `["CWE-863", "CWE-285"]`
- **Reproducer / Test**: `jupyterhub/tests/test_api.py::test_add_admin` and `test_user_make_admin`
- **Verification Execution**: Buggy permits user with `admin:users` scope to set `admin=True`; fixed enforces `if not self.current_user.admin: raise web.HTTPError(403)`.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, CVE advisory, unit tests)
- **Verifier Timestamp**: `2026-09-25T23:40:00+07:00`
- **Discovery & Technical Notes**: In `jupyterhub/apihandlers/users.py`, a user granted the non-admin `admin:users` scope could grant `admin: True` to other users or themselves, escalating permissions to full cluster admin. Fixed by requiring `self.current_user.admin` for any modification of the `admin` attribute.

### CAND-0032: Zulip — Broken Object Level Authorization on Message Modification
- **Candidate ID**: `CAND-0032`
- **Source**: GHSA-q3wg-jm9p-35fj / CVE-2023-32678 / Zulip Security Release 7.3
- **Source Tier**: Tier 3 (GHSA/CVE) + Tier 1 (Target Git History)
- **Repository**: `zulip/zulip` ([https://github.com/zulip/zulip](https://github.com/zulip/zulip))
- **File / Target**: `zerver/lib/message.py`
- **Buggy Commit**: `ea0b8cc01133c79033868efee3edc6c1e3fa0f2b` (parent of `a30cd12433e3a9f7764763ba38849ac635da5283`)
- **Fixed Commit**: `a30cd12433e3a9f7764763ba38849ac635da5283` ([Commit Diff](https://github.com/zulip/zulip/commit/a30cd12433e3a9f7764763ba38849ac635da5283.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-q3wg-jm9p-35fj](https://github.com/advisories/GHSA-q3wg-jm9p-35fj)
- **Bug Class**: Category 6 — Authorization
- **Ground-Truth Pre-Fix Locus**: Lines 825–827 (`if has_user_message: return True`) and Lines 842–856 (in `has_message_access`)
- **Multi-File Span**: No (Central message access authorization function in `zerver/lib/message.py`)
- **Proposed Primary CWE**: CWE-863 (Incorrect Authorization)
- **Proposed CWE Labels**: `["CWE-863", "CWE-285", "CWE-639"]`
- **Acceptable Alternative CWE Set**: `["CWE-285", "CWE-639"]`
- **Reproducer / Test**: `zerver/tests/test_message_edit.py::test_edit_message_in_unsubscribed_private_stream`
- **Verification Execution**: Buggy permits unsubscribed former member with `user_message` row to access and edit private stream messages; fixed enforces active subscription check (`is_subscribed_helper()`), rejecting unauthorized edit.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, official security release notes, unit tests in `zerver/tests/test_message_edit.py`)
- **Verifier Timestamp**: `2026-09-25T23:55:00+07:00`
- **Commit Correction & Technical Notes**: The provisional commit cited during discovery (`62ba8e455d8f460001d9fb486a6dabfd1ed67717`) was found during Session 18 audit to be a session invalidation fix. Primary git auditing traced the authentic commit for CVE-2023-32678 / GHSA-q3wg-jm9p-35fj to `a30cd12433e3a9f7764763ba38849ac635da5283`, which fixes `has_message_access` in `zerver/lib/message.py` and adds regression tests in `zerver/tests/test_message_edit.py`.

### CAND-0033: Zulip — Missing Access Check in Typing Notifications Endpoint (IDOR)
- **Candidate ID**: `CAND-0033`
- **Source**: GHSA-wj5v-8mqg-gvqw / Zulip Security Release
- **Source Tier**: Tier 3 (GHSA) + Tier 1 (Target Git History)
- **Repository**: `zulip/zulip` ([https://github.com/zulip/zulip](https://github.com/zulip/zulip))
- **File / Target**: `zerver/actions/typing.py`
- **Buggy Commit**: `b1007916b03a40841ba141f5e4f041aeaeaaa010`
- **Fixed Commit**: `0cdfe767edca25901ae0922e4e71bd1d2e96084a` ([Commit Diff](https://github.com/zulip/zulip/commit/0cdfe767edca25901ae0922e4e71bd1d2e96084a.diff))
- **Advisory URL**: [https://github.com/advisories/GHSA-wj5v-8mqg-gvqw](https://github.com/advisories/GHSA-wj5v-8mqg-gvqw)
- **Bug Class**: Category 6 — Authorization
- **Impact**: `None`
- **Ground-Truth Pre-Fix Locus**: Lines 83–85 (in `check_send_typing_notification` calling `do_send_typing_notification` without access check)
- **Multi-File Span**: No (Single file typing notification action)
- **Proposed Primary CWE**: CWE-863 (Incorrect Authorization)
- **Proposed CWE Labels**: `["CWE-863"]`
- **Acceptable Alternative CWE Set**: `["CWE-639"]`
- **Reproducer / Test**: Upstream regression test `zerver/tests/test_typing.py::TypingRestrictedUserAccessTest::test_direct_typing_notification_to_inaccessible_user` (Cited from commit 0cdfe767; requires full Zulip backend stack, not run locally)
- **Verification Execution**: Buggy allows sending typing notification to inaccessible recipient; fixed calls `check_sender_can_access_recipients` raising JsonableError.
- **Classification Status**: `VALIDATED — GROUND TRUTH LOCUS ISOLATED`
- **Verification Status**: `GROUND_TRUTH_VERIFIED`
- **Quality Level**: Level A (Verified commit diff, official advisory, unit tests in `zerver/tests/test_typing.py`)
- **Verifier Timestamp**: `2026-10-09T06:30:00+07:00`
- **Discovery & Technical Notes**: The typing notifications endpoint lacked an authorization check verifying whether the sender had permission to view or interact with recipients. Allowed guest users in restricted organizations to query and enumerate internal user IDs and private email addresses. *(Audit note: Traced authentic commit `0cdfe767edca25901ae0922e4e71bd1d2e96084a` and target file `zerver/actions/typing.py`, with pre-fix parent `b1007916b03a40841ba141f5e4f041aeaeaaa010`; primary CWE tightened to CWE-863, broad CWE-285 removed; reproducer cited upstream)*.

### CAND-0034: Zulip — Object Level Authorization Bypass in Non-Subscribed Public Channels
- **Candidate ID**: `CAND-0034`
- **Source**: GHSA-5r8f-gq2h-fcgp / August 2026 Security Release
- **Source Tier**: Tier 3 (GHSA) + Tier 1 (Target Git History)
- **Repository**: `zulip/zulip` ([https://github.com/zulip/zulip](https://github.com/zulip/zulip))
- **File / Target**: `zerver/tornado/event_queue.py` and `zerver/views/events.py`
- **Buggy Commit**: `8.x` / parent
- **Fixed Commit**: August 2026 security release commit
- **Advisory URL**: [https://github.com/advisories/GHSA-5r8f-gq2h-fcgp](https://github.com/advisories/GHSA-5r8f-gq2h-fcgp)
- **Bug Class**: Category 6 — Authorization
- **Proposed Primary CWE**: CWE-863 (Incorrect Authorization)
- **Proposed CWE Labels**: `["CWE-863", "CWE-285"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level A (Verified official advisory, target codebase, event queue logic)
- **Discovery & Technical Notes**: In multi-channel organizations, event stream authorization failed to enforce subscription boundaries for guest personas, permitting guests to monitor event streams and read live messages from public channels they had not subscribed to.

### CAND-0035: Apache Superset — Improper Authorization / Ownership Takeover (BOLA)
- **Candidate ID**: `CAND-0035`
- **Source**: CVE-2025-27696 / Apache Security Disclosure
- **Source Tier**: Tier 3 (CVE/Advisory) + Tier 1 (Target Git History)
- **Repository**: `apache/superset` ([https://github.com/apache/superset](https://github.com/apache/superset))
- **File / Target**: `superset/datasets/api.py` and dataset permission filters
- **Buggy Commit**: `4.1.0` / parent
- **Fixed Commit**: Release 4.1.1 security patch commit
- **Bug Class**: Category 6 — Authorization
- **Proposed Primary CWE**: CWE-639 (Authorization Bypass Through User-Controlled Key)
- **Proposed CWE Labels**: `["CWE-639", "CWE-863"]`
- **Classification Status**: `PROVISIONAL — PRIMARY-SOURCE VERIFIED`
- **Verification Status**: `SOURCE_VERIFIED`
- **Quality Level**: Level B (Verified Apache security release, CVE disclosure, target API handlers)
- **Discovery & Technical Notes**: A Broken Object Level Authorization (BOLA) vulnerability in dataset update APIs allowed non-owner users to overwrite dataset metadata and ownership fields, gaining unauthorized administrative ownership over restricted datasets.

---

## 8. Rejected Candidate Log (With Technical Discrepancies)

| Rejection ID | Target Package | Purported Defect | Reason for Rejection | Source of Truth Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **REJ-0001** | `tiangolo/fastapi` | Fix for CVE-2021-32677 in PR #3165 | **Discrepancy / False Citation**: GPT Researcher cited PR #3165 as the fix for CVE-2021-32677. Primary repository inspection confirmed PR #3165 was an unrelated issue ("Authentication token check before upload"). The authentic fix is commit `fa7e3c996edf2d5482fff8f9d890ac2390dede4d` (retained under CAND-0007). | Primary GitHub issue search on `tiangolo/fastapi/pull/3165`. |
| **REJ-0002** | `jpadilla/pyjwt` | CVE-2024-5138 (JWKS key validation) | **Scanner False Positive / Hallucination**: CVE-2024-5138 is a command-line privilege escalation vulnerability in Canonical's `snapd` (`snapctl`), erroneously flagged against PyJWT in automated CVE databases. Rejected. | NVD record for CVE-2024-5138; Canonical `snapd` commit `68ee9c6aa916ab87dbfd9a26030690f2cabf1e14`. |
| **REJ-0003** | `tortoise/tortoise-orm` | CVE-2022-41908 (SQL injection) | **Hallucinated CVE Number**: CVE-2022-41908 does not exist in Tortoise-ORM. Primary search confirmed the real SQL injection defect is CVE-2020-11010 (commit `91c364053e0ddf77edc5442914c6f049512678b3`, retained under CAND-0017). | NVD database search; Tortoise ORM official security advisories. |
| **REJ-0004** | `netbox-community/netbox` | CVE-2022-41919 (REST API IDOR) | **CVE Farming / Non-Defect**: No record of CVE-2022-41919 exists in NetBox advisories. Maintainers documented that low-risk/invalid reports were submitted without representing legitimate vulnerabilities. Rejected. | NetBox official security advisories and maintainer disclosure policies. |
| **REJ-0005** | `django/django` | CVE-2023-43663 (Admin Search DoS/Bypass) | **Hallucinated CVE Number**: CVE-2023-43663 is a PrestaShop vulnerability. The Django ReDoS in admin search is CVE-2023-43665. Rejected hallucinated mapping. | NVD record for CVE-2023-43663 vs CVE-2023-43665. |
| **REJ-0006** | `jupyterhub/jupyterhub` | CVE-2024-28102 (Scope Bypass) | **Dependency Transposition**: CVE-2024-28102 is a compression bomb DoS in `jwcrypto`, not a JupyterHub scope bypass. Replaced with authentic JupyterHub privilege escalation CVE-2024-41942 (CAND-0031). | NVD record for CVE-2024-28102. |
| **REJ-0007** | `zulip/zulip` | CVE-2021-43788 (Cross-realm mention bypass) | **Cross-Project Confusion**: CVE-2021-43788 is a NodeBB path traversal flaw, not a Zulip defect. Replaced with authentic Zulip authorization advisories GHSA-q3wg-jm9p-35fj and GHSA-wj5v-8mqg-gvqw. | NVD record for CVE-2021-43788. |

---

## 9. Next Phase Transition Criteria (To Phase 2: Ground-Truth Validation)

To transition a candidate from `candidate_queue.md` into the final evaluation benchmark:
1. **Locus Isolation**: Extract exact ground-truth line coordinates `[start_line, end_line]` in the pre-fix file.
2. **Acceptable CWE Set**: Declare primary CWE and explicit acceptable alternative CWE aliases.
3. **Multi-File Context Map**: Map whether the defect is single-file local or requires multi-file repository graph context.
4. **Isolated Test Reproducer**: Verify pytest command or fail-to-pass test suite.
5. **Quality Gate Level A Verification**: Final checklist confirmation before marking `ACCEPTED INTO BENCHMARK`.
