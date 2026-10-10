# Candidate Advisory-ID Existence Audit Evidence Suite

- **Scope**: All 36 Candidates in Benchmark Staging Queue (including CAND-0036 Reserve Candidate)
- **Status**: **100% Verified (30 / 30 Security Advisories Confirmed with HTTP 200 OK; 6 Category 1 Functional Flaws with No Advisory Applicable)**
- **Audit Tool**: `audit_advisories.py`
- **Output Artifacts**:
  - `manifest.json`: Full metadata, severity, published date, census counts, and snapshot mapping for all 30 unique advisories.
  - `candidate_mappings.json`: Exact candidate-to-advisory relationships across all 36 candidates.
  - `snapshots/*.json`: 30 raw, authentic JSON responses retrieved directly from GitHub Advisory APIs.

---

## 1. Census Reconciliation & Methodology

### Advisory Count Reconciliation
A prior report summary cited "27 / 27 Security Advisories Confirmed with HTTP 200 OK", while 30 candidate-advisory checks and 30 snapshot files were present. This discrepancy is reconciled as follows:
- **Total Candidates in Queue**: 36 candidates (`CAND-0001` through `CAND-0036`).
- **Category 1 Functional Logic Flaws**: 6 candidates (`CAND-0001` to `CAND-0006`) are pure functional logic flaws with no CVE or GHSA identifiers.
- **Security Defect Candidates**: 30 candidates (`CAND-0007` to `CAND-0035` plus `CAND-0036`).
- **Global Ecosystem Advisory API (`/advisories/{id}`)**: 27 queries (all returned HTTP 200 OK).
- **Repository-Scoped Advisory API (`/repos/zulip/zulip/security-advisories/{id}`)**: 3 queries for Zulip Server (`CAND-0032`, `CAND-0033`, `CAND-0034`), all returned HTTP 200 OK.
- **Total Verified Advisories**: 27 + 3 = **30 verified security advisories** (100% HTTP 200 OK).
- **Total Snapshots on Disk**: Exactly 30 JSON files in `snapshots/`.

The earlier summary cited "27/27" by referencing only the global ecosystem queries, inadvertently omitting the 3 repository-scoped advisories from the summary numerator/denominator even though all 30 snapshots were present on disk.

### Scope Distinction
This suite is strictly an **Advisory-ID Existence Audit**:
- It confirms that every declared GHSA/CVE identifier exists on an authoritative GitHub Advisory endpoint and retrieves authentic JSON metadata snapshots.
- It does **not** evaluate defect-vulnerability equivalence or ground-truth locus precision (those are evaluated independently via the Candidate-to-Advisory Relevance Audit and Pilot Upstream Git Audit).

---

## 2. Investigation & Resolution of Zulip Advisories

A prior integrity audit reported HTTP 404 (Not Found) errors when querying GitHub's global advisory endpoint for Zulip advisories `GHSA-wj5v-8mqg-gvqw`, `GHSA-5r8f-gq2h-fcgp`, and `GHSA-q3wg-jm9p-35fj`.

### Root Cause Analysis:
GitHub maintains two distinct security advisory REST API surfaces:
1. **Global Ecosystem Advisory API** (`/advisories/{ghsa_id}`):
   - Curated for package ecosystems (PyPI, npm, Maven, RubyGems, Go, NuGet).
   - Only indexes vulnerabilities in software distributed as library packages.
2. **Repository Security Advisory API** (`/repos/{owner}/{repo}/security-advisories/{ghsa_id}`):
   - Published directly by project maintainers in repository security tabs.
   - Indexes vulnerabilities in application servers, web apps, and standalone projects.

Because Zulip is a self-hosted server application rather than a PyPI-distributed package, Zulip maintainers publish advisories directly through the repository security surface.

### Dual-Probe Verification:
The automated test runner probed both endpoints for each Zulip advisory:

| Advisory ID | Candidate | CVE | Global Endpoint (`/advisories/...`) | Repository Endpoint (`/repos/zulip/zulip/...`) | Advisory Summary |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`GHSA-q3wg-jm9p-35fj`** | `CAND-0032` | CVE-2023-32678 | **HTTP 404 Not Found** | **HTTP 200 OK** | *Insufficient authorization check for edition/deletion of messages and topics in private streams by former subscribers* |
| **`GHSA-wj5v-8mqg-gvqw`** | `CAND-0033` | *N/A (Zulip 12.3)* | **HTTP 404 Not Found** | **HTTP 200 OK** | *Missing access check in typing endpoint exposed inaccessible users' IDs and emails* |
| **`GHSA-5r8f-gq2h-fcgp`** | `CAND-0034` | *N/A (Zulip 8.x)* | **HTTP 404 Not Found** | **HTTP 200 OK** | *Guests can read new messages in non-subscribed public channels* |

**Conclusion**: All three Zulip advisories are 100% authentic, published GitHub Security Advisories. Full JSON payloads have been captured in `snapshots/`.

---

## 3. Comprehensive Candidate Advisory Ledger

| Candidate ID | Category | Target Repository | Defect Type | Advisory / CVE | GHSA ID | API Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **CAND-0001** | Cat 1: Logic | `tornadoweb/tornado` | Functional Logic | N/A | N/A | *Not Applicable* |
| **CAND-0002** | Cat 1: Logic | `tiangolo/fastapi` | Functional Logic | N/A | N/A | *Not Applicable* |
| **CAND-0003** | Cat 1: Logic | `cookiecutter/cookiecutter` | Functional Logic | N/A | N/A | *Not Applicable* |
| **CAND-0004** | Cat 1: Logic | `cookiecutter/cookiecutter` | Functional Logic | N/A | N/A | *Not Applicable* |
| **CAND-0005** | Cat 1: Logic | `scrapy/scrapy` | Functional Logic | N/A | N/A | *Not Applicable* |
| **CAND-0006** | Cat 1: Logic | `scrapy/scrapy` | Functional Logic | N/A | N/A | *Not Applicable* |
| **CAND-0007** | Cat 2: Validation | `tiangolo/fastapi` | Security Flaw | CVE-2021-32677 | `GHSA-8h2j-cgx8-6xv7` | **200 OK** |
| **CAND-0008** | Cat 2: Validation | `Kludex/python-multipart` | Security Flaw | CVE-2024-24762 | `GHSA-2jv5-9r88-3w3p` | **200 OK** |
| **CAND-0009** | Cat 2: Validation | `pallets/jinja` | Security Flaw | CVE-2024-34064 | `GHSA-h75v-3vvj-5mfj` | **200 OK** |
| **CAND-0010** | Cat 2: Validation | `urllib3/urllib3` | Security Flaw | CVE-2023-43804 | `GHSA-v845-jxx5-vc9f` | **200 OK** |
| **CAND-0011** | Cat 2: Validation | `aio-libs/aiohttp` | Security Flaw | CVE-2023-49082 | `GHSA-xx9p-xxvh-7g8j` | **200 OK** |
| **CAND-0012** | Cat 2: Validation | `psf/requests` | Security Flaw | CVE-2023-32681 | `GHSA-j8r2-6x86-q33q` | **200 OK** |
| **CAND-0036** | Cat 2: Validation | `django/django` | Security Flaw | CVE-2020-13254 | `GHSA-wpjr-j57x-wxfw` | **200 OK** |
| **CAND-0013** | Cat 3: SQL | `django/django` | Security Flaw | CVE-2025-64459 | `GHSA-frmv-pr5f-9mcr` | **200 OK** |
| **CAND-0014** | Cat 3: SQL | `django/django` | Security Flaw | CVE-2022-34265 | `GHSA-p64x-8rxx-wf6q` | **200 OK** |
| **CAND-0015** | Cat 3: SQL | `django/django` | Security Flaw | CVE-2020-7471 | `GHSA-hmr4-m2h5-33qx` | **200 OK** |
| **CAND-0016** | Cat 3: SQL | `django/django` | Security Flaw | CVE-2021-35042 | `GHSA-xpfp-f569-q3p2` | **200 OK** |
| **CAND-0017** | Cat 3: SQL | `tortoise/tortoise-orm` | Security Flaw | CVE-2020-11010 | `GHSA-9j2c-x8qm-qmjq` | **200 OK** |
| **CAND-0018** | Cat 3: SQL | `sqlalchemy/sqlalchemy` | Security Flaw | CVE-2019-7164 | `GHSA-887w-45rq-vxgf` | **200 OK** |
| **CAND-0019** | Cat 4: Path | `aio-libs/aiohttp` | Security Flaw | CVE-2024-23334 | `GHSA-5h86-8mv2-jq9f` | **200 OK** |
| **CAND-0020** | Cat 4: Path | `pallets/werkzeug` | Security Flaw | CVE-2024-49766 | `GHSA-f9vj-2wh5-fj8j` | **200 OK** |
| **CAND-0021** | Cat 4: Path | `encode/starlette` | Security Flaw | CVE-2023-29159 | `GHSA-v5gw-mw7f-84px` | **200 OK** |
| **CAND-0022** | Cat 4: Path | `django/django` | Security Flaw | CVE-2021-31542 | `GHSA-rxjp-mfm9-w4wr` | **200 OK** |
| **CAND-0023** | Cat 4: Path | `tornadoweb/tornado` | Security Flaw | CVE-2023-28370 | `GHSA-hj3f-6gcp-jg8j` | **200 OK** |
| **CAND-0024** | Cat 4: Path | `mlflow/mlflow` | Security Flaw | CVE-2023-1177 | `GHSA-xg73-94fp-g449` | **200 OK** |
| **CAND-0025** | Cat 5: Auth | `jpadilla/pyjwt` | Security Flaw | CVE-2022-29217 | `GHSA-ffqj-6fqr-9h24` | **200 OK** |
| **CAND-0026** | Cat 5: Auth | `paramiko/paramiko` | Security Flaw | CVE-2018-7750 | `GHSA-232r-66cg-79px` | **200 OK** |
| **CAND-0027** | Cat 5: Auth | `lepture/authlib` | Security Flaw | CVE-2026-28802 | `GHSA-7wc2-qxgw-g8gg` | **200 OK** |
| **CAND-0028** | Cat 5: Auth | `lepture/authlib` | Security Flaw | CVE-2024-37568 | `GHSA-5357-c2jx-v7qh` | **200 OK** |
| **CAND-0029** | Cat 5: Auth | `django/django` | Security Flaw | CVE-2024-45231 | `GHSA-rrqc-c2jx-6jgv` | **200 OK** |
| **CAND-0030** | Cat 5: Auth | `mpdavis/python-jose` | Security Flaw | CVE-2024-33663 | `GHSA-6c5p-j8vq-pqhj` | **200 OK** |
| **CAND-0031** | Cat 6: Authz | `jupyterhub/jupyterhub` | Security Flaw | CVE-2024-41942 | `GHSA-9x4q-3gxw-849f` | **200 OK** |
| **CAND-0032** | Cat 6: Authz | `zulip/zulip` | Security Flaw | CVE-2023-32678 | `GHSA-q3wg-jm9p-35fj` | **200 OK** |
| **CAND-0033** | Cat 6: Authz | `zulip/zulip` | Security Flaw | N/A | `GHSA-wj5v-8mqg-gvqw` | **200 OK** |
| **CAND-0034** | Cat 6: Authz | `zulip/zulip` | Security Flaw | N/A | `GHSA-5r8f-gq2h-fcgp` | **200 OK** |
| **CAND-0035** | Cat 6: Authz | `apache/superset` | Security Flaw | CVE-2025-27696 | `GHSA-w6c7-j32f-rq8j` | **200 OK** |

---

## 4. Candidate-to-Advisory Relevance & Taxonomy Audit

A separate audit tool, `audit_relevance.py`, confirms deep semantic relevance across all 18 canonical candidates (3 per category) and reserve candidate `CAND-0036`:

### Key Relevance Verification Dimensions:
1. **Package / Repository Matching**:
   - Every security advisory matches the candidate repository or target PyPI package (`fastapi`, `jinja2`, `python-multipart`, `django`, `tortoise-orm`, `aiohttp`, `werkzeug`, `starlette`, `pyjwt`, `authlib`, `jupyterhub`, `zulip`, `apache-superset`).
2. **Defect & Vulnerability Correspondence**:
   - Defect descriptions match authoritative advisory texts (e.g. unvalidated JSON body parsing for `CAND-0007`, catastrophic ReDoS backtracking for `CAND-0008`, `xmlattr` quote breakout for `CAND-0009`, `Trunc/Extract` date injection for `CAND-0014`, symlink traversal for `CAND-0019`, and BOLA private stream access for `CAND-0032`).
3. **Deployment Models (PyPI Packages vs Standalone Servers)**:
   - **PyPI Package Releases**: Libraries like `fastapi`, `jinja2`, and `django` are distributed through PyPI with semantic version ranges (`vulnerable_version_range`, `first_patched_version`).
   - **Standalone Server Applications (Zulip)**: Applications like `zulip/zulip` are deployed directly from Git revisions, release tarballs, or container images rather than imported from PyPI. Zulip maintains repository-level advisories (`/repos/zulip/zulip/security-advisories/...`) that link directly to pull requests and commit hashes.
4. **CAND-0036 Taxonomy Correction (CWE-20 vs Erroneous NVD CWE-295)**:
   - Upstream advisory `GHSA-wpjr-j57x-wxfw` (CVE-2020-13254) is tagged in the NVD feed with `CWE-295` ("Improper Certificate Validation").
   - Inspection of the actual defect and patch (commit `84b2da5552e100ae3294f564f6c862fef8d0e693` in `django/core/cache/backends/memcached.py`) demonstrates that the fix implements cache key validation (`validate_key(key)`) to reject control characters and whitespace.
   - The thesis taxonomy correctly classifies `CAND-0036` under **`CWE-20` (Improper Input Validation)**, noting and correcting the upstream NVD clerical mistagging.

---

## 5. Reproduction

To re-execute the advisory audits:
```bash
# 1. Advisory-ID Existence Audit (verifies API endpoints & captures snapshots)
python data/evidence/advisory_audit/audit_advisories.py --cached

# 2. Candidate-to-Advisory Relevance Audit (verifies semantic match & taxonomy)
python data/evidence/advisory_audit/audit_relevance.py
```
Outputs are written deterministically to `manifest.json`, `candidate_mappings.json`, `relevance_report.json`, and `snapshots/`.
