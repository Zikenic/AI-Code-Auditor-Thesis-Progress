# Phase 2 Batch 1: Ground-Truth Validation & Locus Isolation Report

> **Document Status**: AUDITED, CORRECTED & UPDATED (Phase 3C Complete)
> **Initial Report Date**: 2026-10-09 (Session 26)
> **Evidence Audit Date**: 2026-10-09 (Session 27)
> **Phase 3C Replacement Date**: 2026-10-09 (Session 40)
> **Scope**: 6 candidates evaluated (1 candidate per category across Categories 1–6).
> **Outcome**: All 6 candidates promoted to `GROUND_TRUTH_VERIFIED` (CAND-0003 formally replaced by CAND-0006 in Phase 3C).<br>
> **Benchmark Status**: Strictly **0** cases accepted into the final benchmark (`ACCEPTED INTO BENCHMARK = 0`).

---

## 0. Evidence Audit & Correction Addendum (Session 27 & Session 40)

### 0.1 Session 27 Evidence Audit Findings
An independent evidence audit of the Session 26 Batch 1 claims identified several data-integrity and verification gaps that were transparently resolved against authentic upstream Git repositories:
- **CAND-0003 (cookiecutter)**: Pre-fix locus corrected to line 85. Upstream reproducer was blocked locally due to missing `binaryornot`. Omitting `encoding='utf-8'` is an I/O locale issue (authoritative CWE-176) rather than a clean fit for Category 1 domain logic. Status confirmed as `SOURCE_VERIFIED` (Approved for Replacement in Curation Phase).
- **CAND-0008 (python-multipart)**: Corrected from 2 conflated defects to 1 single defect (lines 72–75). ReDoS conclusively demonstrated via controlled subprocess benchmark (>50,000× slowdown at N=36); promoted to `GROUND_TRUTH_VERIFIED` (`reproducer_status = executed_confirmed`).
- **CAND-0015 (django)**: Locus lines 54–58 verified. Confirmed as `GROUND_TRUTH_VERIFIED` (`reproducer_status = cited_not_run` due to PostgreSQL service requirement).
- **CAND-0020 (werkzeug)**: Locus lines 151–157 verified. Runtime constraint documented (Windows + Python < 3.11). Confirmed as `GROUND_TRUTH_VERIFIED` (`reproducer_status = attempted_blocked`).
- **CAND-0026 (paramiko)**: Locus lines 1822–1828 in `transport.py` verified; `common.py` designated as contextual file. Advisory updated to authentic `GHSA-232r-66cg-79px`. Confirmed as `GROUND_TRUTH_VERIFIED` (`reproducer_status = cited_not_run`).
- **CAND-0033 (zulip)**: Locus lines 83–85 in `typing.py` verified; primary CWE tightened to CWE-863. Confirmed as `GROUND_TRUTH_VERIFIED` (`reproducer_status = cited_not_run`).

### 0.2 Session 40 (Phase 3C) Replacement Addendum: CAND-0006 Replaces CAND-0003
In Phase 3C, the pending candidate `CAND-0003` was replaced in the canonical dataset (`data/pilot_cases.json`) by **`CAND-0006`** (`scrapy/scrapy`, `scrapy/utils/datatypes.py:318-319`).
- **Replacement Rationale**: Missing `encoding='utf-8'` in CAND-0003 was an I/O locale/decoding flaw (CWE-176) with a blocked reproducer (`binaryornot`). In contrast, `CAND-0006` is a textbook Category 1 NoneType boundary condition defect: `LocalCache.__init__(limit=None)` caused `len(self) >= self.limit` to raise `TypeError: '>=' not supported between instances of 'int' and 'NoneType'` on insertion.
- **Verification Evidence**: Atomic 2-line fix (`if self.limit:`) in commit `439a3e59b8`. Standalone reproducer executed locally with 100% confirmation (`data/evidence/CAND-0006/reproduce_cand_0006.py`). Self-contained 330-line file (~2,800 tokens) perfectly fits Tier 1 whole-file protocol.
- **Historical Evidence Preservation**: All primary-source evidence and audit findings for `CAND-0003` are preserved below in Section 2.

---

## 1. Audited Batch 1 Summary Table

| Candidate ID | Category | Repository | Affected File | Pre-Fix Locus | Primary CWE | Alternative CWE Set | Reproducer Status | Final Status | Quality |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **CAND-0006** | Cat 1: Logic | `scrapy/scrapy` | `scrapy/utils/datatypes.py` | Lines 318–319 | CWE-476 | `["CWE-670"]` | `executed_confirmed` (TypeError on LocalCache without limit) | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0008** | Cat 2: Validation | `Kludex/python-multipart` | `multipart/multipart.py` | Lines 72–75 | CWE-1333 | `["CWE-400"]` | `executed_confirmed` (>50,000x ReDoS slowdown at N=36) | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0015** | Cat 3: SQL | `django/django` | `django/contrib/postgres/aggregates/general.py` | Lines 54–58 | CWE-89 | `["CWE-943"]` | `cited_not_run` (PostgreSQL service required) | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0020** | Cat 4: Path | `pallets/werkzeug` | `src/werkzeug/security.py` | Lines 151–157 | CWE-22 | `["CWE-20"]` | `attempted_blocked` (Windows + Py<3.11 only) | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0026** | Cat 5: Auth | `paramiko/paramiko` | `paramiko/transport.py` | Lines 1822–1828 | CWE-287 | `["CWE-305"]` | `cited_not_run` (SSH harness required) | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0033** | Cat 6: Authz | `zulip/zulip` | `zerver/actions/typing.py` | Lines 83–85 | CWE-863 | `["CWE-639"]` | `cited_not_run` (Zulip stack required) | `GROUND_TRUTH_VERIFIED` | Level A |

*(Historical Note: CAND-0003 [cookiecutter/generate.py:85, CWE-176, attempted_blocked] was audited in Batch 1 as SOURCE_VERIFIED and replaced by CAND-0006 in Phase 3C; its full historical record is preserved below in Section 2).*

---

## 2. Detailed Candidate Records (Audited)

### CAND-0006: Scrapy — NoneType Comparison Guard in LocalCache
- **Candidate ID**: `CAND-0006`
- **Category**: Category 1 — Boundary / Conditional / Logic (NoneType boundary)
- **Impact Attribute**: `functional`
- **Repository URL**: `https://github.com/scrapy/scrapy.git`
- **Buggy Commit SHA**: `f02c3d1dcf3e4880388d19e961e7911be5dc54ff` (parent of fix commit)
- **Fixed Commit SHA**: `439a3e59b8e858441f8d97dbc32f398db392330d` (`Fix scrapy.utils.datatypes.LocalCache limit issue`)
- **Affected File Path**: `scrapy/utils/datatypes.py`
- **Audited Pre-Fix Locus**: **Lines 318–319** (`while len(self) >= self.limit:` / `self.popitem(last=False)`)
- **Multi-File Span**: No (Single file utility module)
- **Pre-Fix Source Code (Buggy Commit `f02c3d1d`)**:
  ```python
  313:     def __init__(self, limit=None):
  314:         super(LocalCache, self).__init__()
  315:         self.limit = limit
  316:
  317:     def __setitem__(self, key, value):
  318:         while len(self) >= self.limit:
  319:             self.popitem(last=False)
  320:         super(LocalCache, self).__setitem__(key, value)
  ```
- **Fix Diff**:
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
- **Reproducer Audit**: Upstream unit tests `tests/test_utils_datatypes.py::LocalCacheTest::test_cache_without_limit` and `test_cache_with_limit`. Executed locally via standalone script `data/evidence/CAND-0006/reproduce_cand_0006.py`; confirmed that `LocalCache()` without limit raises `TypeError: '>=' not supported between instances of 'int' and 'NoneType'` on insertion in the buggy revision, and succeeds in the fixed revision.
- **Taxonomy & CWE Assessment**:
  - Primary CWE: **CWE-476** (NULL Pointer / NoneType Dereference)
  - Acceptable Alternative CWE: `["CWE-670"]` (Always-Incorrect Control Flow Implementation)
  - Category 1 Scope Fit: Pure Category 1 boundary/condition defect.
- **Phase 3C Promotion**: Promoted to canonical dataset (`data/pilot_cases.json`) in Phase 3C as the verified replacement for CAND-0003.
- **Reproducer Status**: `executed_confirmed`
- **Final Status**: **`GROUND_TRUTH_VERIFIED`**
- **Quality Level**: Level A (Verified commit diff, unit tests in `tests/test_utils_datatypes.py`, executed and confirmed local reproducer)

---

### CAND-0003 (Archived Historical Record — Replaced in Canonical Dataset by CAND-0006 in Phase 3C): Cookiecutter — Missing UTF-8 Encoding Parameter in Context Loading
- **Candidate ID**: `CAND-0003`
- **Category**: Category 1 — Boundary / Conditional / Logic (Disputed Scope Fit)
- **Impact Attribute**: `functional`
- **Repository URL**: `https://github.com/cookiecutter/cookiecutter.git`
- **Buggy Commit SHA**: `c15633745df6abdb24e02746b82aadb20b8cdf8c` (parent of fix commit)
- **Fixed Commit SHA**: `7f6804c4953a18386809f11faf4d86898570debc` (`Fix default values being loaded with wrong encoding on Windows (#1414)`)
- **Affected File Path**: `cookiecutter/generate.py`
- **Audited Pre-Fix Locus**: **Line 85** (`with open(context_file) as file_handle:`)
  *(Note: Line 83 in buggy commit is empty; earlier report of line 83 was an unverified hunk header miscalculation).*
- **Multi-File Span**: No
- **Pre-Fix Source Code (Buggy Commit `c1563374`)**:
  ```python
  82:     context = OrderedDict([])
  83:
  84:     try:
  85:         with open(context_file) as file_handle:
  86:             obj = json.load(file_handle, object_pairs_hook=OrderedDict)
  ```
- **Fix Diff**:
  ```diff
  --- a/cookiecutter/generate.py
  +++ b/cookiecutter/generate.py
  @@ -82,7 +82,7 @@ def generate_context(
       try:
  -        with open(context_file) as file_handle:
  +        with open(context_file, encoding='utf-8') as file_handle:
  ```
- **Reproducer Audit**: Upstream regression test `tests/test_generate_context.py::test_generate_context_decodes_non_ascii_chars` with `non_ascii.json`. **Not executed locally** because uninstalled external dependency `binaryornot` is required.
- **Taxonomy & CWE Assessment**:
  - Primary CWE: CWE-20 (Improper Input Validation) — Technically weak; the input file is not invalid, rather `open()` defaults to the system locale. Authoritative CWE is CWE-176 (Improper Handling of Unicode Encoding).
  - Alternative CWE: CWE-670.
  - Category 1 Scope Fit: Missing `encoding` parameter is an I/O locale boundary issue rather than core business domain logic.
- **Recommendation & Disposition**: Replaced in the canonical dataset during Phase 3C by CAND-0006. Historical primary-source evidence preserved here.
- **Final Status**: **`SOURCE_VERIFIED` (Historical Archive — Replaced in Canonical Dataset)**

---

### CAND-0008: python-multipart — ReDoS in Content-Type Options Header Parsing
- **Candidate ID**: `CAND-0008`
- **Category**: Category 2 — Input Validation / Sanitization
- **Impact Attribute**: `None`
- **Repository URL**: `https://github.com/Kludex/python-multipart.git`
- **Buggy Commit SHA**: `d3d16dae4b061c34fe9d3c9081d9800c49fc1f7a` (parent of fix commit)
- **Fixed Commit SHA**: `20f0ef6b4e4caf7d69a667c54dff57fe467109a4` (`Refactor header option parser to use standard library instead of custom RegEx (#75)`)
- **Advisory / CVE**: GHSA-2jv5-9r88-3w3p / CVE-2024-24762
- **Affected File Path**: `multipart/multipart.py`
- **Audited Pre-Fix Locus**: **Lines 72–75** (`OPTION_RE_STR` and `OPTION_RE = re.compile(...)`). Call site at lines 101–117 is recorded as usage context.
- **Defect Count Correction**: Represents **1 single defect** (ReDoS vulnerability in option parsing), NOT 2 distinct defects.
- **Pre-Fix Source Code (Buggy Commit `d3d16dae`)**:
  ```python
  72: OPTION_RE_STR = (
  73:     br'(?:;|^)\s*([^' + SPECIAL_CHARS + br']+)\s*=\s*(' + VALUE_STR + br')'
  74: )
  75: OPTION_RE = re.compile(OPTION_RE_STR)
  ...
  101:     for match in OPTION_RE.finditer(rest):
  ```
- **Fix Diff**: Deprecated `OPTION_RE`; replaced regex parsing loop with standard library `email.message.Message`.
- **Reproducer Audit**: Executed authentic upstream advisory PoC payload (`header = 'application/x-www-form-urlencoded; !="' + ('\\' * N)`) across buggy commit `d3d16dae` vs fixed commit `20f0ef6b` in controlled benchmark subprocesses using a median-of-five protocol across bounded $N \in [20, 36]$ (documented in `data/evidence/CAND-0008/`). Demonstrated experimentally observed exponential growth over the tested range (with unproven $O(2^{N/2})$ formula formally retracted): buggy execution time scaled from 0.000638s at $N=20$ to 1.338705s at $N=36$, exceeding a 50,000× slowdown relative to fixed constant time (~0.000026s across all $N$). ReDoS conclusively demonstrated.
- **CWE Assessment**: Primary: **CWE-1333** (Inefficient Regular Expression Complexity). Acceptable alternative: `{"CWE-400"}`. Overly broad generic parent `CWE-20` removed.
- **Reproducer Status**: `executed_confirmed`
- **Final Status**: **`GROUND_TRUTH_VERIFIED`**

---

### CAND-0015: Django — SQL Injection in PostgreSQL `StringAgg` Delimiter
- **Candidate ID**: `CAND-0015`
- **Category**: Category 3 — SQL / ORM Injection
- **Impact Attribute**: `None`
- **Repository URL**: `https://github.com/django/django.git`
- **Buggy Commit SHA**: `6b178a3e930f72069f3cda2e6a09d1b320fc09ec` (parent of fix commit)
- **Fixed Commit SHA**: `eb31d845323618d688ad429479c6dda973056136` (`Fixed CVE-2020-7471 -- Properly escaped StringAgg(delimiter) parameter`)
- **Advisory / CVE**: GHSA-hmr4-m2h5-33qx / CVE-2020-7471 (supersedes invalid GHSA-hmr4-m2h5-3347)
- **Affected File Path**: `django/contrib/postgres/aggregates/general.py`
- **Audited Pre-Fix Locus**: **Lines 54–58**
- **Pre-Fix Source Code (Buggy Commit `6b178a3e`)**:
  ```python
  52: class StringAgg(OrderableAggMixin, Aggregate):
  53:     function = 'STRING_AGG'
  54:     template = "%(function)s(%(distinct)s%(expressions)s, '%(delimiter)s'%(ordering)s)"
  55:     allow_distinct = True
  56:
  57:     def __init__(self, expression, delimiter, **extra):
  58:         super().__init__(expression, delimiter=delimiter, **extra)
  ```
- **Fix Diff**:
  ```diff
  --- a/django/contrib/postgres/aggregates/general.py
  +++ b/django/contrib/postgres/aggregates/general.py
  @@ -54,5 +54,6 @@ class StringAgg(OrderableAggMixin, Aggregate):
  -    template = "%(function)s(%(distinct)s%(expressions)s, '%(delimiter)s'%(ordering)s)"
  +    template = '%(function)s(%(distinct)s%(expressions)s %(ordering)s)'
       def __init__(self, expression, delimiter, **extra):
  -        super().__init__(expression, delimiter=delimiter, **extra)
  +        delimiter_expr = Value(str(delimiter))
  +        super().__init__(expression, delimiter_expr, **extra)
  ```
- **Reproducer Audit**: Upstream regression test `tests/postgres_tests/test_aggregates.py::test_string_agg_delimiter_escaping` cited from commit `eb31d845`. **Not executed locally** (requires PostgreSQL test database server).
- **CWE Assessment**: Primary: **CWE-89** (SQL Injection). Acceptable alternative: `{"CWE-943"}` (Special Elements in Data Query Logic). Broad parent `CWE-20` removed.
- **Final Status**: **`GROUND_TRUTH_VERIFIED`**

---

### CAND-0020: Werkzeug — Safe_Join UNC Path Traversal on Windows
- **Candidate ID**: `CAND-0020`
- **Category**: Category 4 — Path Traversal / Unsafe File Operations
- **Impact Attribute**: `None`
- **Repository URL**: `https://github.com/pallets/werkzeug.git`
- **Buggy Commit SHA**: `50cfeebcb0727e18cc52ffbeb125f4a66551179b` (parent of merge commit)
- **Fixed Commit SHA**: `2767bcb10a7dd1c297d812cc5e6d11a474c1f092` (merge of `87cc78a2`: `catch special absolute path on Windows Python < 3.11`)
- **Advisory / CVE**: GHSA-f9vj-2wh5-fj8j / CVE-2024-49766 (supersedes invalid GHSA-mvgw-hpx7-xrqc)
- **Affected File Path**: `src/werkzeug/security.py`
- **Audited Pre-Fix Locus**: **Lines 151–157**
- **Pre-Fix Source Code (Buggy Commit `50cfeebc`)**:
  ```python
  151:         if (
  152:             any(sep in filename for sep in _os_alt_seps)
  153:             or os.path.isabs(filename)
  154:             or filename == ".."
  155:             or filename.startswith("../")
  156:         ):
  157:             return None
  ```
- **Fix Diff**:
  ```diff
  --- a/src/werkzeug/security.py
  +++ b/src/werkzeug/security.py
  @@ -153,2 +153,4 @@ def safe_join(directory: str, *pathnames: str) -> str | None:
               or os.path.isabs(filename)
  +            # ntpath.isabs doesn't catch this on Python < 3.11
  +            or filename.startswith("/")
  ```
- **Reproducer Audit**: Upstream regression test `tests/test_security.py::test_safe_join` with `("//b/c", None)`. Defect only manifested on Windows when running Python < 3.11. On the local development environment (Windows 11, Python 3.12.10), standard library `ntpath.isabs("//b/c")` returns `True`. **Cited from upstream; not locally reproducible in Python 3.12**.
- **CWE Assessment**: Primary: **CWE-22** (Path Traversal). Acceptable alternative: `{"CWE-20"}`.
- **Final Status**: **`GROUND_TRUTH_VERIFIED`**

---

### CAND-0026: Paramiko — State Machine Authentication Bypass in Transport Loop
- **Candidate ID**: `CAND-0026`
- **Category**: Category 5 — Authentication
- **Impact Attribute**: `None`
- **Repository URL**: `https://github.com/paramiko/paramiko.git`
- **Buggy Commit SHA**: `aefd28a7f00c4250d113d375e96abf5da3eb89f9` (parent of fix commit)
- **Fixed Commit SHA**: `fa29bd8446c8eab237f5187d28787727b4610516` (`Fixes CVE-2018-7750 / #1175`)
- **Advisory / CVE**: **GHSA-232r-66cg-79px** / CVE-2018-7750 *(earlier reported GHSA-8h46-5p95-gcmg was invalid 404)*
- **Affected File Path**: `paramiko/transport.py`
- **Audited Pre-Fix Locus**: **Lines 1822–1828** (single matchable finding locus)
- **Contextual Files**: `paramiko/common.py` (constant definition `HIGHEST_USERAUTH_MESSAGE_ID = 79`)
- **Pre-Fix Source Code (Buggy Commit `aefd28a7`)**:
  ```python
  1822:                     if ptype in self._handler_table:
  1823:                         self._handler_table[ptype](self, m)
  1824:                     elif ptype in self._channel_handler_table:
  1825:                         chanid = m.get_int()
  1826:                         chan = self._channels.get(chanid)
  1827:                         if chan is not None:
  1828:                             self._channel_handler_table[ptype](chan, m)
  ```
- **Fix Diff**: Added `_ensure_authed(ptype, m)` before dispatching handler; returns `MSG_CHANNEL_OPEN_FAILURE` if unauthenticated.
- **Reproducer Audit**: Cited from issue #1175. Live end-to-end SSH handshake verification requires interactive SSH test harness. **Cited, not executed locally**.
- **CWE Assessment**: Primary: **CWE-287** (Improper Authentication). Acceptable alternative: `{"CWE-305"}` (Authentication Bypass by Primary Weakness). Overly broad authorization label `CWE-285` removed.
- **Final Status**: **`GROUND_TRUTH_VERIFIED`**

---

### CAND-0033: Zulip — Missing Access Check in Typing Notifications Endpoint (IDOR)
- **Candidate ID**: `CAND-0033`
- **Category**: Category 6 — Authorization (BOLA / IDOR / Scopes)
- **Impact Attribute**: `None`
- **Repository URL**: `https://github.com/zulip/zulip.git`
- **Buggy Commit SHA**: `b1007916b03a40841ba141f5e4f041aeaeaaa010` (parent of fix commit)
- **Fixed Commit SHA**: `0cdfe767edca25901ae0922e4e71bd1d2e96084a` (`typing_notifications: Check that the sender can access recipients. Advisory: GHSA-wj5v-8mqg-gvqw`)
- **Advisory**: GHSA-wj5v-8mqg-gvqw (cited in upstream commit message)
- **Affected File Path**: `zerver/actions/typing.py`
- **Audited Pre-Fix Locus**: **Lines 83–85**
- **Pre-Fix Source Code (Buggy Commit `b1007916`)**:
  ```python
  83:         user_profiles.append(user_profile)
  84:
  85:     do_send_typing_notification(
  ```
- **Fix Diff**:
  ```diff
  --- a/zerver/actions/typing.py
  +++ b/zerver/actions/typing.py
  @@ -83,2 +83,4 @@ def check_send_typing_notification(
           user_profiles.append(user_profile)
  +
  +    check_sender_can_access_recipients(sender, user_profiles)
  ```
- **Reproducer Audit**: Upstream regression test `zerver/tests/test_typing.py::TypingRestrictedUserAccessTest::test_direct_typing_notification_to_inaccessible_user` cited in commit `0cdfe767`. **Not executed locally** (requires Zulip backend stack).
- **CWE Assessment**: Primary: **CWE-863** (Incorrect Authorization). Acceptable alternative: `{"CWE-639"}` (Authorization Bypass Through User-Controlled Key / IDOR). Broad parent `CWE-285` removed.
- **Final Status**: **`GROUND_TRUTH_VERIFIED`**

---

## 3. The 10-Point Ground-Truth Acceptance Checklist Evaluation (Audited)

| Criteria | CAND-0003 | CAND-0008 | CAND-0015 | CAND-0020 | CAND-0026 | CAND-0033 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Identifiable Buggy State** | PASS (`c156337`) | PASS (`d3d16da`) | PASS (`6b178a3`) | PASS (`50cfeeb`) | PASS (`aefd28a`) | PASS (`b100791`) |
| **2. Documented Defect Evidence** | PASS (PR #1414) | PASS (GHSA-2jv5) | PASS (GHSA-hmr4) | PASS (GHSA-mvgw) | PASS (GHSA-232r) | PASS (GHSA-wj5v) |
| **3. Identifiable Affected Locus** | PASS (`generate.py:85`) | PASS (`multipart.py:72-75`) | PASS (`general.py:54-58`) | PASS (`security.py:151-157`) | PASS (`transport.py:1822-1828`) | PASS (`typing.py:83-85`) |
| **4. Reproducer / Verification Test** | FAIL (Not run) | PASS (Locally executed PoC) | PASS (Cited upstream) | PASS (Cited upstream) | PASS (Cited upstream) | PASS (Cited upstream) |
| **5. Identifiable Fixed State** | PASS (`7f6804c`) | PASS (`20f0ef6`) | PASS (`eb31d84`) | PASS (`2767bcb`) | PASS (`fa29bd8`) | PASS (`0cdfe76`) |
| **6. Verified Fix** | PASS (UTF-8 encoding) | PASS (`email.message`) | PASS (`Value()` binding) | PASS (`startswith('/')`) | PASS (`_ensure_authed()`) | PASS (`check_sender_can_access`) |
| **7. Justified Category Assignment** | FAIL (Disputed Cat 1) | PASS (Cat 2: Validation) | PASS (Cat 3: SQL) | PASS (Cat 4: Path) | PASS (Cat 5: Auth) | PASS (Cat 6: Authz) |
| **8. Justified CWE Assignment** | FAIL (Debatable CWE-20) | PASS (CWE-1333 / 400) | PASS (CWE-89 / 943) | PASS (CWE-22 / 20) | PASS (CWE-287 / 305) | PASS (CWE-863 / 639) |
| **9. Within Thesis Scope** | PASS (Python CLI) | PASS (Python ASGI) | PASS (Python Web) | PASS (Python WSGI) | PASS (Python SSH) | PASS (Python Web) |
| **10. Non-Duplicate** | PASS (Unique) | PASS (Unique) | PASS (Unique) | PASS (Unique) | PASS (Unique) | PASS (Unique) |
| **Final Checklist Gate** | **FAIL** | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |
| **Audited Status** | **SOURCE_VERIFIED** | **GROUND_TRUTH_VERIFIED** | **GROUND_TRUTH_VERIFIED** | **GROUND_TRUTH_VERIFIED** | **GROUND_TRUTH_VERIFIED** | **GROUND_TRUTH_VERIFIED** |
| **Reproducer Enum Status** | `attempted_blocked` | `executed_confirmed` | `cited_not_run` | `attempted_blocked` | `cited_not_run` | `cited_not_run` |

---

## 4. Paramiko Advisory Reconciliation & Recomputed Census

### 4.1 Authoritative Paramiko Advisory Reconciliation (CAND-0026)

Live API queries against GitHub Advisory API and NIST NVD established:
1. **GitHub Advisory API Query**:
   - `GET https://api.github.com/advisories/GHSA-232r-66cg-79px` -> **HTTP 200 OK**
     - Summary: *"Paramiko not properly checking authentication before processing other requests"*
     - CVE Alias: `CVE-2018-7750`
     - Advisory CWEs: `[{"cwe_id": "CWE-287", "name": "Improper Authentication"}]`
     - Severity: `critical`
   - `GET https://api.github.com/advisories/GHSA-8h46-5p95-gcmg` -> **HTTP 404 Not Found** (`{"message":"Not Found"}`)
     - Reconciled: `GHSA-8h46-5p95-gcmg` was an invalid ID and has been fully replaced by authentic `GHSA-232r-66cg-79px`.
2. **NVD API Query**:
   - `GET https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2018-7750` -> **HTTP 200 OK**
     - Primary CWE: `CWE-287` (Improper Authentication, source: `nvd@nist.gov`).
3. **CWE Selection Justification**:
   - **Primary CWE**: `CWE-287` (directly endorsed by both GitHub Advisory and NVD).
   - **Alternative CWE**: `CWE-305` (*Authentication Bypass by Primary Weakness*, child of CWE-287 representing state machine bypass before authentication verification).
   - Overly broad parent `CWE-285` (*Improper Authorization*) is eliminated.
4. **Target vs. Contextual File Isolation**:
   - Matchable target: `paramiko/transport.py` (lines 1822–1828).
   - Contextual file: `paramiko/common.py` (declares protocol constants such as `MSG_USERAUTH_SUCCESS`; non-buggy).

### 4.2 Recomputed Deterministic Census (via `tools/compute_census.py`)

- **Canonical Dataset (`data/pilot_cases.json`)**:
  - Total canonical cases: **18** (17 `GROUND_TRUTH_VERIFIED`, 1 `SOURCE_VERIFIED`).
  - Total defect records: **23** (22 in GT verified cases, 1 in pending case).
  - Distinct defect loci (ranges): **23**.
  - Distinct target files: **17** (`fastapi/routing.py` is shared by `CAND-0002` and `CAND-0007`).
  - Distinct contextual files: **1** (`paramiko/common.py`).
  - File union: **18**.
- **Staging Queue (`candidate_queue.md`)**:
  - Staged candidates: **36** (18 `GROUND_TRUTH_VERIFIED` incl. reserve `CAND-0036`, 18 `SOURCE_VERIFIED` incl. pending `CAND-0003`).
  - Lifecycle arithmetic: $36 - 17\ \text{canonical verified} = 19\ \text{not canonically verified}$ ($18\ \text{SV} + 1\ \text{reserve CAND-0036}$).
  - Separate rejected leads register: **7** (`REJ-0001` through `REJ-0007`).
  - Benchmark accepted cases: Strictly **0 / 100**.

