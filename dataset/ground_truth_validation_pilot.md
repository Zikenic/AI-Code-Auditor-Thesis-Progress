# Phase 2 Pilot: Ground-Truth Validation & Locus Isolation Report

> **Status**: PILOT COMPLETED (12 of 12 Pilot Candidates Verified)  
> **Date**: 2026-09-25  
> **Scope**: 12 candidates total (exactly 2 candidates across each of the 6 locked categories).  
> **Acceptance Rule**: Locus line coordinates refer strictly to the **pre-fix / buggy state**. Primary and alternative CWE sets are pre-declared prior to benchmark evaluation.

---

## 1. Pilot Summary Table

| Candidate ID | Category | Repository | Affected File | Pre-Fix Locus | Primary CWE | Alternative CWE Set | Status | Quality |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- | :---: | :---: |
| **CAND-0001** | Cat 1: Logic | `tornadoweb/tornado` | `tornado/http1connection.py` | 390–394 | CWE-670 | `["CWE-440", "CWE-20"]` | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0002** | Cat 1: Logic | `tiangolo/fastapi` | `fastapi/routing.py` | 498–502 | CWE-670 | `["CWE-440"]` | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0007** | Cat 2: Validation | `tiangolo/fastapi` | `fastapi/routing.py` | 182–184 | CWE-352 | `["CWE-20", "CWE-345"]` | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0009** | Cat 2: Validation | `pallets/jinja` | `src/jinja2/filters.py` | 292–293 | CWE-79 | `["CWE-20", "CWE-116"]` | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0014** | Cat 3: SQL | `django/django` | `django/db/models/functions/datetime.py` | 45–51, 225–236 | CWE-89 | `["CWE-20", "CWE-943"]` | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0017** | Cat 3: SQL | `tortoise/tortoise-orm` | `tortoise/backends/mysql/executor.py` | 19–45 | CWE-89 | `["CWE-943", "CWE-20"]` | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0019** | Cat 4: Path | `aio-libs/aiohttp` | `aiohttp/web_urldispatcher.py` | 643–645 | CWE-22 | `["CWE-59", "CWE-20"]` | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0021** | Cat 4: Path | `encode/starlette` | `starlette/staticfiles.py` | 172–172 | CWE-22 | `["CWE-20"]` | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0025** | Cat 5: Auth | `jpadilla/pyjwt` | `jwt/algorithms.py` | 186–197 | CWE-347 | `["CWE-287", "CWE-327"]` | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0027** | Cat 5: Auth | `lepture/authlib` | `authlib/jose/__init__.py` | 49–49 | CWE-347 | `["CWE-287", "CWE-327"]` | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0031** | Cat 6: Authz | `jupyterhub/jupyterhub` | `jupyterhub/apihandlers/users.py` | 265–267, 328–331 | CWE-269 | `["CWE-863", "CWE-285"]` | `GROUND_TRUTH_VERIFIED` | Level A |
| **CAND-0032** | Cat 6: Authz | `zulip/zulip` | `zerver/lib/message.py` | 825–827, 842–856 | CWE-863 | `["CWE-285", "CWE-639"]` | `GROUND_TRUTH_VERIFIED` | Level A |

---

## 2. Detailed Candidate Records

### CAND-0001: Tornado — HTTP Chunking Output Logic Flaw
- **Candidate ID**: `CAND-0001`
- **Category**: Category 1 — Boundary / Conditional / Logic
- **Impact Attribute**: `functional`
- **Repository**: `tornadoweb/tornado` (https://github.com/tornadoweb/tornado)
- **Buggy Commit SHA**: `2ca8821d006f6693f920a4b183a3a7c985a5c8ad`
- **Fixed Commit SHA**: `4f486a4aec746e9d66441600ee3b0743228b061c`
- **Affected File Path**: `tornado/http1connection.py`
- **Ground-Truth Pre-Fix Locus**: Lines 390–394 (specifically line 393: `and "Transfer-Encoding" not in headers`)
- **Multi-File Span**: No (Single file local defect)
- **Locus Rationale**: In `write_headers`, chunking determination logic checked `"Transfer-Encoding" not in headers`. When a client supplied `Transfer-Encoding: chunked`, this condition evaluated to `False`, inadvertently disabling output chunking.
- **Defect Summary**: Logic error in HTTP/1.1 header writing caused chunked transfer encoding to be suppressed when explicitly requested.
- **Reproducer / Test**: Upstream regression test `tornado/test/httpclient_test.py::test_redirect_put_with_body`.
- **Buggy-State Execution**: Chunking disabled (`chunking_output == False`), payload body truncated/malformed.
- **Fixed-State Execution**: Chunking enabled (`chunking_output == True`), tests pass cleanly.
- **Primary CWE**: CWE-670 (Always-Incorrect Control Flow Implementation)
- **Acceptable Alternative CWE Set**: `["CWE-440", "CWE-20"]`
- **Evidence Quality Level**: Level A (Verified git diff, reproducible test case, atomic 3-line fix)
- **Final Status**: `GROUND_TRUTH_VERIFIED`

---

### CAND-0002: FastAPI — WebSocket Route Dependency Overrides Omission
- **Candidate ID**: `CAND-0002`
- **Category**: Category 1 — Boundary / Conditional / Logic
- **Impact Attribute**: `functional`
- **Repository**: `tiangolo/fastapi` (https://github.com/tiangolo/fastapi)
- **Buggy Commit SHA**: `210af1fd3dc0f612a08fa02a0cb3f5adb81e5bfb`
- **Fixed Commit SHA**: `02441ff0313d5b471b662293244c53e712f1243f`
- **Affected File Path**: `fastapi/routing.py`
- **Ground-Truth Pre-Fix Locus**: Lines 498–502 (specifically line 501: `route = APIWebSocketRoute(path, endpoint=endpoint, name=name)`)
- **Multi-File Span**: No (Single file local defect)
- **Locus Rationale**: `add_api_websocket_route` instantiated `APIWebSocketRoute` without forwarding `dependency_overrides_provider=self.dependency_overrides_provider`.
- **Defect Summary**: Omission of parameter forwarding caused dependency injection overrides defined on the router/app level to be ignored for WebSocket endpoints.
- **Reproducer / Test**: Upstream regression test `tests/test_ws_router.py::test_router_ws_depends_with_override`.
- **Buggy-State Execution**: `route.dependency_overrides_provider is None`; overrides ignored in WebSocket endpoints.
- **Fixed-State Execution**: `route.dependency_overrides_provider` correctly propagated; overrides applied.
- **Primary CWE**: CWE-670 (Always-Incorrect Control Flow Implementation)
- **Acceptable Alternative CWE Set**: `["CWE-440"]`
- **Evidence Quality Level**: Level A (Verified git diff, unit test suite, isolated bug in routing logic)
- **Final Status**: `GROUND_TRUTH_VERIFIED`

---

### CAND-0007: FastAPI — Content-Type Validation Bypass (CSRF via JSON Body)
- **Candidate ID**: `CAND-0007`
- **Category**: Category 2 — Input Validation / Sanitization
- **Impact Attribute**: `security`
- **Repository**: `tiangolo/fastapi` (https://github.com/tiangolo/fastapi)
- **Buggy Commit SHA**: `90120dd6e83d997fa2f7f54119a2e0cf906b1ded`
- **Fixed Commit SHA**: `fa7e3c996edf2d5482fff8f9d890ac2390dede4d`
- **Advisory / CVE**: GHSA-8h2j-cgx8-6xv7 / CVE-2021-32677
- **Affected File Path**: `fastapi/routing.py`
- **Ground-Truth Pre-Fix Locus**: Lines 182–184 (`body_bytes = await request.body(); if body_bytes: body = await request.json()`)
- **Multi-File Span**: No (Single file core routing dispatch logic)
- **Locus Rationale**: In `get_request_handler.app`, FastAPI parsed incoming request bodies with `await request.json()` without checking `request.headers.get("content-type")`. Cross-origin browsers could send simple `text/plain` requests without CORS preflight, which were then processed as authenticated JSON requests.
- **Defect Summary**: Missing Content-Type header validation allowed cross-site request forgery against JSON endpoints.
- **Reproducer / Test**: Upstream regression test `tests/test_tutorial/test_body/test_tutorial001.py::test_wrong_headers`.
- **Buggy-State Execution**: `text/plain` payload parsed as JSON, returning HTTP 200 (CSRF exploitable).
- **Fixed-State Execution**: Content-Type verified via `email.message.Message`; `text/plain` rejected with HTTP 422 Unprocessable Entity.
- **Primary CWE**: CWE-352 (Cross-Site Request Forgery)
- **Acceptable Alternative CWE Set**: `["CWE-20", "CWE-345"]`
- **Evidence Quality Level**: Level A (Verified advisory, official security fix commit, regression tests)
- **Final Status**: `GROUND_TRUTH_VERIFIED`

---

### CAND-0009: Jinja2 — XML/HTML Attribute Injection in `xmlattr`
- **Candidate ID**: `CAND-0009`
- **Category**: Category 2 — Input Validation / Sanitization
- **Impact Attribute**: `security`
- **Repository**: `pallets/jinja` (https://github.com/pallets/jinja)
- **Buggy Commit SHA**: `a7863ba9d3521f1450f821119c50d19d7ecea329`
- **Fixed Commit SHA**: `0668239dc6b44ef38e7a6c9f91f312fd4ca581cb`
- **Advisory / CVE**: GHSA-h75v-3vvj-5mfj / CVE-2024-34064
- **Affected File Path**: `src/jinja2/filters.py`
- **Ground-Truth Pre-Fix Locus**: Line 250 (`_space_re = re.compile(r"\s", flags=re.ASCII)`) and Lines 292–293 (`if _space_re.search(key) is not None: raise ValueError(...)`)
- **Multi-File Span**: No (Single file filter definition)
- **Locus Rationale**: `do_xmlattr` checked attribute keys only against whitespace (`\s`). Characters such as `/`, `>`, or `=` were permitted, allowing an attacker providing dictionary keys to break out of attribute quotes and inject new attributes or handlers (e.g. `onclick=alert(1)`).
- **Defect Summary**: Incomplete character sanitization in HTML template attribute filter permitted attribute injection and cross-site scripting.
- **Reproducer / Test**: Upstream regression test `tests/test_filters.py::test_xmlattr_key_invalid`.
- **Buggy-State Execution**: Keys with `/`, `>`, or `=` passed without error, producing injected HTML attributes.
- **Fixed-State Execution**: Regex updated to `r"[\s/>=]"`; invalid characters raise `ValueError`.
- **Primary CWE**: CWE-79 (Improper Neutralization of Input During Web Page Generation)
- **Acceptable Alternative CWE Set**: `["CWE-20", "CWE-116"]`
- **Evidence Quality Level**: Level A (Verified commit diff, CVE advisory, comprehensive parameterized pytest)
- **Final Status**: `GROUND_TRUTH_VERIFIED`

---

### CAND-0014: Django — SQL Injection in `Trunc()` and `Extract()`
- **Candidate ID**: `CAND-0014`
- **Category**: Category 3 — SQL / ORM Injection
- **Impact Attribute**: `security`
- **Repository**: `django/django` (https://github.com/django/django)
- **Buggy Commit SHA**: `425718726b7d2edd7b8a043f8976e437262b5098`
- **Fixed Commit SHA**: `54eb8a374d5d98594b264e8ec22337819b37443c`
- **Advisory / CVE**: GHSA-4w5c-wffp-v8c6 / CVE-2022-34265
- **Affected File Path**: `django/db/models/functions/datetime.py` (and pattern in `django/db/backends/base/operations.py`)
- **Ground-Truth Pre-Fix Locus**: Lines 45–51 (in `Extract.__init__`) and Lines 225–236 (in `Trunc.__init__`)
- **Multi-File Span**: Yes (Locus in `datetime.py`; regex pattern helper defined in `operations.py`)
- **Locus Rationale**: Untrusted user input passed into `Extract(lookup_name=...)` or `Trunc(kind=...)` was evaluated directly into SQL date extraction and truncation functions in `as_sql` without character validation.
- **Defect Summary**: Unsanitized parameters in ORM datetime functions allowed SQL injection via crafted lookup names.
- **Reproducer / Test**: Upstream regression test `tests/db_functions/datetime/test_extract_trunc.py::test_extract_lookup_name_sql_injection`.
- **Buggy-State Execution**: Payload `"day' FROM start_datetime)) OR 1=1;--"` interpolates into SQL query without error.
- **Fixed-State Execution**: Regex `r"[\w\-_()]+"` strictly validates parameter; raises `ValueError` on malformed inputs.
- **Primary CWE**: CWE-89 (Improper Neutralization of Special Elements used in an SQL Command)
- **Acceptable Alternative CWE Set**: `["CWE-20", "CWE-943"]`
- **Evidence Quality Level**: Level A (Verified security release commit, official release notes, test suite)
- **Final Status**: `GROUND_TRUTH_VERIFIED`

---

### CAND-0017: Tortoise-ORM — SQL Injection in MySQL Filter Lookups
- **Candidate ID**: `CAND-0017`
- **Category**: Category 3 — SQL / ORM Injection
- **Impact Attribute**: `security`
- **Repository**: `tortoise/tortoise-orm` (https://github.com/tortoise/tortoise-orm)
- **Buggy Commit SHA**: `816ff00e988f79b4ff1601f247062bb5eb9db802`
- **Fixed Commit SHA**: `91c364053e0ddf77edc5442914c6f049512678b3`
- **Advisory / CVE**: GHSA-8h28-p98r-5858 / CVE-2020-11010
- **Affected File Path**: `tortoise/backends/mysql/executor.py`
- **Ground-Truth Pre-Fix Locus**: Lines 19–45 (MySQL filter overrides: `mysql_contains`, `mysql_starts_with`, `mysql_ends_with`)
- **Multi-File Span**: Yes (Core executor functions in `mysql/executor.py`; PyPika monkey-patch in `filters.py`)
- **Locus Rationale**: MySQL filter functions formatted values directly into LIKE query criteria via `like(f"%{value}%")` without escaping backslashes, percent signs, or quote delimiters.
- **Defect Summary**: Missing LIKE-clause escaping in MySQL backend allowed SQL injection through filter operations.
- **Reproducer / Test**: Upstream fuzz test harness `tests/test_fuzz.py`.
- **Buggy-State Execution**: Payload with single quotes and wildcards alters SQL query semantics.
- **Fixed-State Execution**: `escape_like()` escapes `\`, `%`, and `_`; wraps constants in sanitized `Like` terms.
- **Primary CWE**: CWE-89 (Improper Neutralization of Special Elements used in an SQL Command)
- **Acceptable Alternative CWE Set**: `["CWE-943", "CWE-20"]`
- **Evidence Quality Level**: Level A (Verified advisory, commit diff, regression fuzz test)
- **Final Status**: `GROUND_TRUTH_VERIFIED`

---

### CAND-0019: aiohttp — Static Route Directory Traversal via Symlink Follow
- **Candidate ID**: `CAND-0019`
- **Category**: Category 4 — Path Traversal / Unsafe File Operations
- **Impact Attribute**: `security`
- **Repository**: `aio-libs/aiohttp` (https://github.com/aio-libs/aiohttp)
- **Buggy Commit SHA**: `33ccdfb0a12690af5bb49bda2319ec0907fa7827`
- **Fixed Commit SHA**: `1c335944d6a8b1298baf179b7c0b3069f10c514b`
- **Advisory / CVE**: GHSA-5h86-8mv2-jq9f / CVE-2024-23334
- **Affected File Path**: `aiohttp/web_urldispatcher.py`
- **Ground-Truth Pre-Fix Locus**: Lines 643–645 (in `_handle`), and Lines 574–576 (in `url_for`)
- **Multi-File Span**: No (Single file static URL dispatcher)
- **Locus Rationale**: In `_handle`, the check `filepath.relative_to(self._directory)` was nested under `if not self._follow_symlinks:`. When `follow_symlinks=True`, path confinement was skipped entirely, allowing directory traversal sequences to access arbitrary files.
- **Defect Summary**: Conditional bypass of directory boundary verification enabled arbitrary file read when symlink following was enabled.
- **Reproducer / Test**: Upstream regression test `tests/test_web_urldispatcher.py::test_follow_symlink_directory_traversal`.
- **Buggy-State Execution**: `GET /../private_file` resolves outside static root and returns file contents.
- **Fixed-State Execution**: `normalized_path.relative_to(self._directory)` is strictly enforced regardless of symlinks; returns HTTP 404.
- **Primary CWE**: CWE-22 (Improper Limitation of a Pathname to a Restricted Directory)
- **Acceptable Alternative CWE Set**: `["CWE-59", "CWE-20"]`
- **Evidence Quality Level**: Level A (Verified CVE advisory, git diff, socket-level reproduction test)
- **Final Status**: `GROUND_TRUTH_VERIFIED`

---

### CAND-0021: Starlette — Commonprefix Directory Escape
- **Candidate ID**: `CAND-0021`
- **Category**: Category 4 — Path Traversal / Unsafe File Operations
- **Impact Attribute**: `security`
- **Repository**: `encode/starlette` (https://github.com/encode/starlette)
- **Buggy Commit SHA**: `24c1fac62a80bb153c6548145334fc643991e35a`
- **Fixed Commit SHA**: `1797de464124b090f10cf570441e8292936d63e3`
- **Advisory / CVE**: GHSA-v5gw-mw7f-84px / CVE-2023-29159
- **Affected File Path**: `starlette/staticfiles.py`
- **Ground-Truth Pre-Fix Locus**: Line 172 (`if os.path.commonprefix([full_path, directory]) != directory:`)
- **Multi-File Span**: No (Single file atomic locus)
- **Locus Rationale**: `lookup_path` used `os.path.commonprefix` to ensure requested paths stayed within the target directory. Because `commonprefix` operates on characters rather than path components, `/static-secret` matched base directory `/static`.
- **Defect Summary**: Character-based prefix comparison allowed sibling directory escape in static file serving.
- **Reproducer / Test**: Upstream regression test `tests/test_staticfiles.py::test_staticfiles_avoids_path_traversal`.
- **Buggy-State Execution**: Access to `/../static_disallow/index.html` succeeds because common string prefix matches.
- **Fixed-State Execution**: `os.path.commonpath` checks path components; access raises HTTP 404.
- **Primary CWE**: CWE-22 (Improper Limitation of a Pathname to a Restricted Directory)
- **Acceptable Alternative CWE Set**: `["CWE-20"]`
- **Evidence Quality Level**: Level A (Verified git diff, official security advisory, unit tests)
- **Final Status**: `GROUND_TRUTH_VERIFIED`

---

### CAND-0025: PyJWT — Key Confusion between HMAC and Asymmetric Keys
- **Candidate ID**: `CAND-0025`
- **Category**: Category 5 — Authentication
- **Impact Attribute**: `security`
- **Repository**: `jpadilla/pyjwt` (https://github.com/jpadilla/pyjwt)
- **Buggy Commit SHA**: `24b29adfebcb4f057a3cef5aaf35653bc0c1c8cc`
- **Fixed Commit SHA**: `9c528670c455b8d948aff95ed50e22940d1ad3fc`
- **Advisory / CVE**: GHSA-ffqj-6fqr-9h24 / CVE-2022-29217
- **Affected File Path**: `jwt/algorithms.py`
- **Ground-Truth Pre-Fix Locus**: Lines 186–197 (in `HMACAlgorithm.prepare_key`)
- **Multi-File Span**: No (Single file key preparation method)
- **Locus Rationale**: `HMACAlgorithm.prepare_key` used an incomplete blacklist of asymmetric header prefixes (`b"-----BEGIN PUBLIC KEY-----"`, `b"ssh-rsa"`). OpenSSH Ed25519 and ECDSA public keys bypassed the blacklist and were treated as raw symmetric HMAC secrets.
- **Defect Summary**: Incomplete asymmetric key validation permitted HMAC signature forgery using public keys.
- **Reproducer / Test**: Upstream regression test `tests/test_advisory.py::TestAdvisory::test_ghsa_ffqj_6fqr_9h24`.
- **Buggy-State Execution**: `jwt.decode(token_signed_with_pubkey_hmac, pub_key_bytes)` validates successfully.
- **Fixed-State Execution**: Comprehensive `is_pem_format()` and `is_ssh_key()` checks reject key with `InvalidKeyError`.
- **Primary CWE**: CWE-347 (Improper Verification of Cryptographic Signature)
- **Acceptable Alternative CWE Set**: `["CWE-287", "CWE-327"]`
- **Evidence Quality Level**: Level A (Verified advisory, commit diff, reproduction test suite)
- **Final Status**: `GROUND_TRUTH_VERIFIED`

---

### CAND-0027: Authlib — Signature Verification Bypass via Algorithm 'none'
- **Candidate ID**: `CAND-0027`
- **Category**: Category 5 — Authentication
- **Impact Attribute**: `security`
- **Repository**: `lepture/authlib` (https://github.com/lepture/authlib)
- **Buggy Commit SHA**: `bb7a315befbad333faf9a23ef574d6e3134a6774`
- **Fixed Commit SHA**: `b87c32ed07b8ae7f805873e1c9cafd1016761df7`
- **Advisory / CVE**: GHSA-7wc2-qxgw-g8gg / CVE-2026-28802
- **Affected File Path**: `authlib/jose/__init__.py`
- **Ground-Truth Pre-Fix Locus**: Line 49 (`jwt = JsonWebToken(list(JsonWebSignature.ALGORITHMS_REGISTRY.keys()))`)
- **Multi-File Span**: No (Global singleton definition)
- **Locus Rationale**: The default global singleton `jwt` was initialized with all algorithms from `JsonWebSignature.ALGORITHMS_REGISTRY`, which included `"none"`. As a result, tokens signed with `"alg": "none"` and an empty signature bypassed verification by default.
- **Defect Summary**: Inclusion of insecure 'none' algorithm in default JWT decoder permitted signature verification bypass.
- **Reproducer / Test**: Upstream tests in `tests/flask/test_oauth2/test_jwt_authorization_request.py::test_server_require_request_object_alg_none`.
- **Buggy-State Execution**: Unsigned token with `"alg": "none"` decoded as valid claims without cryptographic key.
- **Fixed-State Execution**: Default algorithms strictly whitelisted to cryptographic families (`HS256`, `RS256`, etc.); `"none"` rejected.
- **Primary CWE**: CWE-347 (Improper Verification of Cryptographic Signature)
- **Acceptable Alternative CWE Set**: `["CWE-287", "CWE-327"]`
- **Evidence Quality Level**: Level A (Verified commit diff, advisory, test suite)
- **Final Status**: `GROUND_TRUTH_VERIFIED`

---

### CAND-0031: JupyterHub — Privilege Escalation in User Administration API
- **Candidate ID**: `CAND-0031`
- **Category**: Category 6 — Authorization
- **Impact Attribute**: `security`
- **Repository**: `jupyterhub/jupyterhub` (https://github.com/jupyterhub/jupyterhub)
- **Buggy Commit SHA**: `b4053616743eb011e5bb568700f25afca17aef53`
- **Fixed Commit SHA**: `99e2720b0fc626cbeeca3c6337f917fdacfaa428`
- **Advisory / CVE**: GHSA-7996-7454-5223 / CVE-2024-41942
- **Affected File Path**: `jupyterhub/apihandlers/users.py`
- **Ground-Truth Pre-Fix Locus**: Lines 265–267 (in `post(self, user_name)`: `if 'admin' in data: user.admin = data['admin']`) and Lines 328–331 (in `patch(self, user_name)`)
- **Multi-File Span**: No (Single file user API handler)
- **Locus Rationale**: A user with the non-admin `admin:users` scope could create or patch users with `admin=True` without the handler verifying that `self.current_user.admin` was True.
- **Defect Summary**: Missing authorization check allowed users with user-management scopes to grant cluster administrator privileges.
- **Reproducer / Test**: Upstream regression tests `jupyterhub/tests/test_api.py::test_add_admin` and `test_user_make_admin` (parametrized across `is_admin: True, False`).
- **Buggy-State Execution**: Non-admin requester with `admin:users` scope sets `admin: True`, returning HTTP 201/200.
- **Fixed-State Execution**: Check `if not self.current_user.admin: raise web.HTTPError(403)` blocks unauthorized promotion.
- **Primary CWE**: CWE-269 (Improper Privilege Management)
- **Acceptable Alternative CWE Set**: `["CWE-863", "CWE-285"]`
- **Evidence Quality Level**: Level A (Verified CVE advisory, commit diff, unit tests)
- **Final Status**: `GROUND_TRUTH_VERIFIED`

---

### CAND-0032: Zulip — Broken Object Level Authorization on Message Modification
- **Candidate ID**: `CAND-0032`
- **Category**: Category 6 — Authorization
- **Impact Attribute**: `security`
- **Repository**: `zulip/zulip` (https://github.com/zulip/zulip)
- **Buggy Commit SHA**: `ea0b8cc01133c79033868efee3edc6c1e3fa0f2b`
- **Fixed Commit SHA**: `a30cd12433e3a9f7764763ba38849ac635da5283`
- **Advisory / CVE**: GHSA-q3wg-jm9p-35fj / CVE-2023-32678
- **Affected File Path**: `zerver/lib/message.py`
- **Ground-Truth Pre-Fix Locus**: Lines 825–827 (`if has_user_message: return True`) and Lines 842–856 (in `has_message_access`)
- **Multi-File Span**: No (Central message access authorization function in `zerver/lib/message.py`)
- **Locus Rationale**: In `has_message_access`, any user who had previously received a message in a private stream possessed a `UserMessage` database row, causing `has_user_message` to evaluate to `True`. Pre-fix lines 825–827 returned `True` immediately, allowing unsubscribed users to access, edit, or delete messages in private channels they were no longer members of.
- **Defect Summary**: Missing subscription check in `has_message_access` permitted former private stream members to edit or delete messages in streams they were unsubscribed from (Broken Object Level Authorization).
- **Reproducer / Test**: Upstream regression test `zerver/tests/test_message_edit.py::test_edit_message_in_unsubscribed_private_stream`.
- **Buggy-State Execution**: Unsubscribed user issues PATCH to `/json/messages/{msg_id}`; `has_message_access` returns `True`; edit succeeds.
- **Fixed-State Execution**: `has_message_access` requires both `has_user_message` and `is_subscribed_helper()`; returns `False`; edit fails with HTTP 400 `Invalid message(s)`.
- **Primary CWE**: CWE-863 (Incorrect Authorization)
- **Acceptable Alternative CWE Set**: `["CWE-285", "CWE-639"]`
- **Evidence Quality Level**: Level A (Verified commit diff, official security release notes, unit tests in `zerver/tests/test_message_edit.py`)
- **Final Status**: `GROUND_TRUTH_VERIFIED`

---

## 3. Pilot Integrity & Reclassification Log

### Reclassification of CAND-0036 (Category 6 → Category 2)

> During Phase 2 pilot validation, CAND-0036 was found to have been incorrectly classified as Authorization. Primary-source review showed that the vulnerability is more appropriately categorized as Input Validation / Sanitization. The case was reclassified and the Category 6 pilot slot was replaced.

- **Candidate ID**: `CAND-0036`
- **Original Classification**: Category 6 — Authorization (CWE-285)
- **Reclassified Category**: **Category 2 — Input Validation / Sanitization**
- **Impact Attribute**: `security`
- **Repository**: `django/django` (https://github.com/django/django)
- **Buggy Commit SHA**: `1f2dd37f6fcefdd10ed44cb233b2e62b520afb38`
- **Fixed Commit SHA**: `84b2da5552e100ae3294f564f6c862fef8d0e693`
- **Advisory / CVE**: CVE-2020-13254 / Django Security Release (June 3, 2020)
- **Affected File Path**: `django/core/cache/backends/memcached.py`
- **Ground-Truth Pre-Fix Locus**: Lines 65–86 (`add`, `get`, `set`, `delete`, `get_many`)
- **Multi-File Span**: Yes (Missing validation calls in `memcached.py`; validation implementation in `base.py`)
- **Reclassification Rationale**: Django CVE-2020-13254 describes malformed Memcached cache keys containing whitespace or control characters causing command desynchronization and key collisions. The fix adds cache-key validation (`self.validate_key(key)`), raising `InvalidCacheKey`. This defect is fundamentally improper input validation / character sanitization prior to interacting with the backend protocol, not a broken object-level authorization check.
- **Updated Primary CWE**: **CWE-20 (Improper Input Validation)** (CWE-285 removed as inappropriate for input validation flaw)
- **Updated Alternative CWE Set**: `["CWE-116", "CWE-200"]`
- **Reproducer / Test**: `tests/cache/tests.py::_perform_invalid_key_test`
- **Verification Execution**: Buggy state passes control characters and spaces directly to memcached backend; fixed state invokes `validate_key` raising `InvalidCacheKey`.
- **Evidence Quality Level**: Level A (Verified commit diff, security release announcement, unit tests)
- **Lifecycle Status**: `GROUND_TRUTH_VERIFIED` (Staged under Category 2; preserved for full benchmark intake in Phase 3)
