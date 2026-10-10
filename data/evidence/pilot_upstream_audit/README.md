# Pilot Upstream Git Audit Evidence

- **Scope**: 12 Pilot Benchmark Candidates + CAND-0036 Reserve Candidate (13 cases total)
- **Status**: **13 / 13 PASSED (100% Verified)**
- **Audit Tool**: `audit_upstream_pilot.py`
- **Output Record**: `audit_results.json`

---

## 1. Audit Methodology

This evidence suite provides an automated, reproducible, and verifiable audit of the pilot benchmark dataset directly against upstream primary Git repositories.

For every audited candidate:
1. **Authentic Git Repositories**: Authentic Git repositories are inspected from upstream remotes without manual patching or subjective estimation.
2. **Pre-Fix Locus Verification**: The exact target file is extracted from the buggy commit SHA, line counts are computed, and the 1-indexed pre-fix coordinates `[start_line, end_line]` are validated to lie strictly within file boundaries.
3. **Strict In-Locus Anchor Assertion**: Buggy behavioral code anchors are strictly required to appear **within the exact declared line range** (locus snippet), not merely anywhere in the file.
4. **Fix Anchor Verification**: Substrings representing the corrective defensive patch are verified to be present in the fixed commit tree.
5. **Genuine Vulnerability Distinction**: Buggy and fixed revisions are audited independently. For candidates such as `CAND-0007` and `CAND-0017`, the harness explicitly asserts that the anchor conditions genuinely distinguish the vulnerable state from the fixed state (e.g., verifying that unguarded `body = await request.json()` is absent in fixed FastAPI and guarded by Content-Type header inspection; and verifying that unescaped LIKE interpolation is eliminated in fixed Tortoise-ORM and replaced by `escape_like`).
6. **Parity with Pilot Table 1**: All loci correspond exactly to the coordinates published in Table 1 of `ground_truth_validation_pilot.md` and `data/pilot_cases.json`.

---

## 2. Summary of Audited Candidates

| Candidate ID | Target Repository | Affected File | Pre-Fix Locus | Buggy Defect Anchor (In-Locus) | Fixed Patch Anchor | Distinction Verified | Result |
| :--- | :--- | :--- | :---: | :--- | :--- | :---: | :---: |
| **CAND-0001** | `tornadoweb/tornado` | `tornado/http1connection.py` | 390–394 | `and "Transfer-Encoding" not in headers` | `headers["Transfer-Encoding"] == "chunked"` | Yes | **PASS** |
| **CAND-0002** | `tiangolo/fastapi` | `fastapi/routing.py` | 498–502 | `route = APIWebSocketRoute(path, endpoint=endpoint, name=name)` | `dependency_overrides_provider=self.dependency_overrides_provider` | Yes | **PASS** |
| **CAND-0007** | `tiangolo/fastapi` | `fastapi/routing.py` | 182–184 | `body = await request.json()` | `content_type_value = request.headers.get("content-type")` | Yes (Unguarded absent in fixed; header check added) | **PASS** |
| **CAND-0009** | `pallets/jinja` | `src/jinja2/filters.py` | 250, 292–293 | `yield from value.items()` / `if _space_re.search(key) is not None:` | `_attr_key_re = re.compile(r"[\s/>=]", flags=re.ASCII)` | Yes | **PASS** |
| **CAND-0014** | `django/django` | `django/db/models/functions/datetime.py` | 45–51, 225–236 | `self.lookup_name = lookup_name` / `super().__init__(expression, ...)` | `extract_trunc_lookup_pattern` | Yes | **PASS** |
| **CAND-0017** | `tortoise/tortoise-orm` | `tortoise/backends/mysql/executor.py` | 19–45 | `functions.Cast(field, SqlTypes.CHAR).like(f"%{value}%")` | `escape_like` / `StrWrapper` | Yes (Raw LIKE absent in fixed; escape_like added) | **PASS** |
| **CAND-0019** | `aio-libs/aiohttp` | `aiohttp/web_urldispatcher.py` | 574–576, 643–645 | `if not self._follow_symlinks:` / `filepath.relative_to(...)` | `normalized_path.relative_to(self._directory)` | Yes | **PASS** |
| **CAND-0021** | `encode/starlette` | `starlette/staticfiles.py` | 172 | `if os.path.commonprefix([full_path, directory]) != directory:` | `if os.path.commonpath([full_path, directory]) != directory:` | Yes | **PASS** |
| **CAND-0025** | `jpadilla/pyjwt` | `jwt/algorithms.py` | 186–197 | Incomplete blacklist (`b"ssh-rsa"`) | `is_pem_format(key) or is_ssh_key(key)` | Yes | **PASS** |
| **CAND-0027** | `lepture/authlib` | `authlib/jose/__init__.py` | 49 | `jwt = JsonWebToken(list(JsonWebSignature.ALGORITHMS_REGISTRY.keys()))` | `jwt = JsonWebToken(["HS256", ...])` | Yes | **PASS** |
| **CAND-0031** | `jupyterhub/jupyterhub` | `jupyterhub/apihandlers/users.py` | 265–267, 328–331 | `user.admin = data['admin']` | `if not self.current_user.admin:` | Yes | **PASS** |
| **CAND-0032** | `zulip/zulip` | `zerver/lib/message.py` | 825–827, 842–856 | `if has_user_message: return True` / `Subscription.objects.filter` | `is_subscribed_helper()` | Yes | **PASS** |
| **CAND-0036** | `django/django` | `django/core/cache/backends/memcached.py` | 65–86 | `def add(...)` / `def get(...)` without `validate_key` | `self.validate_key(key)` | Yes | **PASS** |

---

## 3. Reproduction

To re-run the full upstream audit:
```bash
python data/evidence/pilot_upstream_audit/audit_upstream_pilot.py
```
Outputs are written deterministically to `audit_results.json`.
