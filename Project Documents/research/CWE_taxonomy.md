# R3 — Focused CWE Taxonomy & Bug Category Research

## Research Status
- **Status**: RESEARCH COMPLETE — AWAITING SUPERVISOR REVIEW
- **Date**: 2026-09-25
- **Investigator**: Antigravity (Repository Executor)
- **Role Boundary**: This artifact gathers authoritative evidence from MITRE CWE, NIST, and Python security standards. **This document presents candidate evidence only. Final taxonomy definition, category selection, and CWE mappings remain the sole responsibility and authority of the student (Bui Van Khai) and supervisor (ThS. Tran Thi Hong Yen).**
- **Independent Verification**: Claude (Pending verification)

---

## 1. Research Objective
For an automated Python Pull Request code-auditing system targeting small-to-medium FastAPI and Flask applications, investigate authoritative Common Weakness Enumeration (CWE) definitions and boundaries for the six working bug categories proposed in the thesis outline.

This research establishes:
1. Which specific candidate CWE IDs correspond to the observed defect types.
2. The hierarchical level (Class, Base, Variant) of each candidate CWE.
3. The exact boundaries between related weaknesses (e.g., input validation vs. downstream injection, authentication vs. authorization, missing vs. incorrect enforcement).
4. Unresolved ambiguities where defects span multiple CWEs or represent non-security functional correctness defects with no clean single CWE mapping.

---

## 2. The Six Working Bug Categories
The thesis outline proposes six working bug categories for pull request review in Python web backends:

1. **Boundary / conditional logic** (off-by-one, incorrect boolean conditions, null / `None` handling)
2. **Input validation & sanitization** (missing/improper input validation, unescaped data, format/type validation)
3. **SQL / ORM injection** (raw SQL concatenation, ORM raw query fragments, data query manipulation)
4. **Path traversal / unsafe file operations** (directory traversal via `../`, arbitrary file write/overwrite, unsafe file upload)
5. **Missing / broken authentication** (unprotected sensitive endpoints, flawed token verification, session/auth bypass)
6. **Missing / broken authorization** (missing access control, IDOR / BOLA, flawed role/permission logic)

---

## 3. Category-by-Category CWE Analysis

### Category 1: Boundary / Conditional Logic
- **Scope & Sub-types**:
  - *Off-by-one*: Looping, array slicing (`list[:n]` vs `list[:n+1]`), boundary inequalities (`<` vs `<=`), pagination offsets.
  - *Incorrect conditions*: Inverted boolean logic (`and` vs `or`, `is` vs `==`), missing edge-case branches, unreachable code paths.
  - *Null / `None` handling*: Missing `None` checks on nullable database columns, optional request fields, dictionary lookups (`dict.get()`), or service returns, causing unhandled `AttributeError: 'NoneType' object has no attribute '...'` or `TypeError`.
- **Candidate CWEs**:
  - **CWE-193: Off-by-one Error** (Base level; child of CWE-682). Specifically covers calculation errors that are off by one in index calculation, loop boundaries, or comparison operators.
  - **CWE-670: Always-Incorrect Control Flow Implementation** (Class level; child of CWE-691). Covers control flow that can never execute as intended due to logic errors.
  - **CWE-480: Use of Incorrect Operator** (Base level; child of CWE-682). Covers using an operator with unintended semantics (e.g., bitwise `&` vs boolean `and`, incorrect comparison operator).
  - **CWE-476: NULL Pointer Dereference** (Base level; child of CWE-710). MITRE officially notes that while originally associated with C/C++, CWE-476 applies to languages supporting null object references. In Python, dereferencing `None` raises `AttributeError` on runtime attribute access.
  - **CWE-754: Improper Check for Unusual or Exceptional Conditions** (Class level) / **CWE-252: Unchecked Return Value** (Base level). Covers failing to verify whether a function returned an exceptional/null value before proceeding.
- **Critical Boundary & Ambiguity**:
  - **Non-Security Functional Defects vs. Security Weaknesses**: The vast majority of boundary and conditional bugs in real-world Python pull requests are **functional correctness / reliability bugs** rather than classical security vulnerabilities (CVEs). They cause wrong return values, broken pagination, or HTTP 500 crashes.
  - MITRE CWE is a security vulnerability taxonomy; its coverage of general functional programming errors is abstract (CWE-682: Incorrect Calculation, CWE-670: Control Flow). General software engineering defect benchmarks (e.g., BugsInPy, SWE-bench) classify these as functional semantic defects rather than mapping them to CWEs.
  - *Recommendation for Thesis*: Do not force a single security CWE onto this category. If included in the benchmark dataset, evaluate whether it should be represented as a composite reliability/correctness category mapping to [CWE-193, CWE-476/CWE-754, CWE-670] or scoped strictly to security-relevant logic gates.

---

### Category 2: Input Validation & Sanitization
- **Scope & Sub-types**:
  - *Missing validation*: Accepting parameters from HTTP request bodies, query strings, or headers without validating type, length, format, or range.
  - *Improper validation*: Using flawed regex patterns, partial allowlists, or client-side-only assumptions.
  - *Inadequate sanitization / encoding*: Passing raw user data into downstream subsystems without escaping or structure enforcement.
- **Candidate CWEs**:
  - **CWE-20: Improper Input Validation** (Class level; child of CWE-707). Software receives input or data, but does not validate or incorrectly validates that the input has the properties that are required to process the data safely and correctly.
  - **CWE-116: Improper Encoding or Escaping of Output** (Class level; child of CWE-707). Software prepares a structured message for another component but fails to encode or escape special characters.
  - **CWE-1287: Improper Validation of Specified Type of Input** (Base level; child of CWE-20). Software expects data of a specific type (e.g., integer, datetime) but fails to validate, allowing unexpected types to bypass checks.
- **Critical Boundary & Ambiguity**:
  - **CWE-20 vs. Downstream Injections (CWE-89, CWE-22, CWE-79)**: MITRE officially cautions that **CWE-20 is frequently misapplied to injection vulnerabilities**. Input validation verifies that input adheres to expected syntactic and structural specifications (e.g., via Pydantic schemas in FastAPI or Marshmallow in Flask). Sanitization/neutralization (CWE-116/CWE-707) modifies or neutralizes data for a specific downstream sink (e.g., SQL compiler, shell interpreter, HTML renderer).
  - *Boundary Rule*: If a defect consists of missing schema validation (e.g., missing Pydantic field constraints, negative numbers allowed for positive quantity), it is **CWE-20 / CWE-1287**. If untrusted input flows into a SQL query or filesystem call, the primary vulnerability is the specific injection weakness (**CWE-89** or **CWE-22**), with CWE-20 acting only as an upstream contributing factor.

---

### Category 3: SQL / ORM Injection
- **Scope & Sub-types**:
  - *Direct SQL Injection*: Raw string interpolation/formatting (`f"SELECT ... WHERE id = '{id}'"`) passed to database execution cursors.
  - *ORM Raw Query Fragments*: Developer invokes ORM methods with unsanitized raw SQL clauses (e.g., SQLAlchemy `session.execute(text(f"..."))`, `filter(text(...))`, or `.order_by(text(user_input))`).
  - *Query Logic Manipulation*: Injecting query structure through unvalidated dictionary keys or dynamic operator parameters in abstract query builders.
- **Candidate CWEs**:
  - **CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')** (Base level; child of CWE-943 and CWE-707). Software constructs all or part of an SQL command using externally-influenced input from an upstream component, but fails to neutralize or incorrectly neutralizes special elements that could modify the intended SQL command.
  - **CWE-943: Improper Neutralization of Special Elements in Data Query Logic** (Class level; child of CWE-707). Software constructs a query or command for a data store (e.g., ORM, NoSQL, LDAP) using externally-influenced input, but fails to neutralize special elements that can alter query logic.
- **Critical Boundary & Ambiguity**:
  - **Does ORM usage change the CWE classification?** No. When an application uses an ORM (SQLAlchemy, Tortoise ORM, Peewee) but constructs raw SQL clauses via string concatenation, the generated command sent to the relational database is still SQL. Authoritative sources (MITRE, OWASP, Semgrep Registry) classify raw SQL fragments in ORMs strictly as **CWE-89**.
  - **When does CWE-943 apply?** CWE-943 is the broader Class-level parent of CWE-89. It applies directly when the query mechanism is non-SQL (e.g., MongoDB/NoSQL query injection, GraphQL query injection, or abstract object query manipulation where relational SQL syntax is not the target).
  - *Recommendation for Thesis*: For relational database backends (PostgreSQL, SQLite, MySQL) using FastAPI/Flask with SQLAlchemy, map this category primarily to **CWE-89**, citing **CWE-943** as the broader architectural query-logic parent.

---

### Category 4: Path Traversal / Unsafe File Operations
- **Scope & Sub-types**:
  - *Path Traversal*: Using user-supplied input containing directory traversal sequences (`../`, `..\`) or absolute paths (`/etc/passwd`, `C:\Windows`) to access files outside the restricted directory.
  - *Arbitrary File Overwrite / Write*: Allowing user-supplied filenames to dictate where files are saved, enabling overwriting configuration or source files.
  - *Unrestricted File Upload*: Accepting files with dangerous extensions (e.g., `.py`, `.sh`, `.html`) that can be executed or served directly.
- **Candidate CWEs**:
  - **CWE-22: Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal')** (Base level; child of CWE-707). Software uses external input to construct a pathname intended to identify a file or directory within a restricted directory, but does not properly neutralize sequences such as `..` that can resolve to a location outside the directory.
  - **CWE-73: External Control of File Name or Path** (Base level; child of CWE-642). Software allows user input to control or influence paths or file names used in filesystem operations.
  - **CWE-434: Unrestricted Upload of File with Dangerous Type** (Base level; child of CWE-707). Software allows the attacker to upload or transfer files of dangerous types that can be processed within the product's environment.
- **Critical Boundary & Ambiguity**:
  - **Path Traversal (CWE-22) vs. External Filename Control (CWE-73)**: CWE-22 specifically requires navigating *out of an intended restricted directory* (typically via `../` or root path substitution). In contrast, CWE-73 occurs whenever user input specifies a filename—even if confined to the target directory—allowing an attacker to specify a filename that overwrites a critical file (e.g., `upload("profile.jpg")` vs. `upload("database.sqlite")`).
  - In Python FastAPI/Flask endpoints handling file uploads or static file serving (e.g., `send_file`, `FileResponse`), path traversal often arises through `os.path.join(base_dir, user_filename)` because in Python's standard library, if `user_filename` starts with `/`, `os.path.join` silently discards `base_dir` and resolves directly to root.
  - *Recommendation for Thesis*: Map this category primarily to **CWE-22** (Path Traversal), with **CWE-73** (External Control of Path) and **CWE-434** (Unrestricted File Upload) documented as associated file-handling weaknesses.

---

### Category 5: Missing / Broken Authentication
- **Scope & Sub-types**:
  - *Missing Authentication*: Endpoints or operations that perform sensitive business actions (e.g., `/admin/users/delete`, `/api/v1/billing/export`) without requiring any user credentials or authentication tokens.
  - *Broken / Improper Authentication*: Authentication mechanism is present but implemented incorrectly (e.g., missing JWT signature verification `verify_signature=False`, hardcoded secret keys, timing vulnerabilities in token comparison, predictable session tokens, improper password hashing).
  - *Authentication Bypass*: Bypassing the authentication barrier through alternate paths, casing quirks, or token spoofing.
- **Candidate CWEs**:
  - **CWE-306: Missing Authentication for Critical Function** (Base level; child of CWE-287). Software does not perform any authentication for functionality that requires a provable user identity or consumes significant resources.
  - **CWE-287: Improper Authentication** (Class level; child of CWE-284). Software does not prove or improperly proves that a claimed identity is valid.
  - **CWE-347: Improper Verification of Cryptographic Signature** (Base level; child of CWE-345). Software does not verify or incorrectly verifies the cryptographic signature for data (critical for JWT / PyJWT token verification bugs in FastAPI).
- **Critical Boundary & Ambiguity**:
  - **Missing (CWE-306) vs. Improper (CWE-287)**: If an API endpoint completely omits the authentication dependency (e.g., forgetting `@router.get(..., dependencies=[Depends(get_current_user)])` in FastAPI), the weakness is strictly **CWE-306**. If the endpoint calls an authentication function, but the function contains cryptographic flaws or accepts unsigned tokens, it is **CWE-287 / CWE-347**.
  - **Authentication (AuthN) vs. Authorization (AuthZ)**: Authentication proves *who the user is* (identity). Authorization proves *what the identified user is allowed to do* (permissions). Conflating the two is a common software engineering error.
  - *Recommendation for Thesis*: Explicitly maintain the distinction between **CWE-306** (endpoint lacks authentication altogether) and **CWE-287** (endpoint has flawed authentication logic), and ensure authentication is strictly distinguished from authorization.

---

### Category 6: Missing / Broken Authorization
- **Scope & Sub-types**:
  - *Missing Authorization (IDOR / BOLA)*: An endpoint verifies that a user is authenticated, but fails to check whether that user has permission to access the specific requested resource (e.g., `GET /api/documents/{doc_id}` returns user B's document to authenticated user A without checking ownership).
  - *Incorrect Authorization*: The authorization check exists, but contains flawed logic (e.g., `if user.role == 'admin' or user.role == 'user': grant_admin_access()`, checking the wrong parameter, or client-supplied role flags).
  - *Privilege Escalation*: Vertical authorization failure allowing standard users to perform administrative actions.
- **Candidate CWEs**:
  - **CWE-862: Missing Authorization** (Base level; child of CWE-285). Software does not perform an authorization check when an actor attempts to access a resource or perform an action.
  - **CWE-863: Incorrect Authorization** (Base level; child of CWE-285). Software performs an authorization check, but the check does not correctly restrict the actor's access.
  - **CWE-639: Authorization Bypass Through User-Controlled Key** (Base level; child of CWE-862/863). The system retrieves or modifies sensitive records based directly on user-controllable keys/IDs without verifying access rights (the canonical CWE for IDOR / OWASP API1: Broken Object Level Authorization).
  - **CWE-285: Improper Authorization** (Class level; child of CWE-284). General umbrella category for authorization defects.
- **Critical Boundary & Ambiguity**:
  - **MITRE Discouraged Mapping for CWE-285**: MITRE explicitly classifies CWE-285 (Improper Authorization) as a **"Discouraged" mapping** because it is too broad and abstract. MITRE strongly advises using the specific base-level weaknesses: **CWE-862** (when the check is completely missing) or **CWE-863** (when the check is present but flawed).
  - **IDOR / BOLA Mapping**: Broken Object Level Authorization (BOLA), the #1 vulnerability on the OWASP API Security Top 10, is precisely modeled by **CWE-639** (User-Controlled Key) and **CWE-862** (Missing Authorization).
  - *Recommendation for Thesis*: Recommend **CWE-862** (Missing Authorization) and **CWE-639** (IDOR/BOLA) as primary candidates, with **CWE-863** (Incorrect Authorization) for logic defects. Avoid using the umbrella CWE-285 as a primary benchmark label.

---

## 4. Candidate CWE Mapping Table

The following table summarizes candidate CWE mappings supported by authoritative primary documentation.

| Working Category | Candidate CWE | CWE Name | Why it fits | Relevant Weakness Definition | Boundary / Ambiguity | Confidence | Primary Source |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Boundary / conditional logic** | **CWE-193** | Off-by-one Error | Captures indexing, slice, and loop count errors off by 1 | Software makes a calculation error that is off by one in calculating loop counts, array offsets, or buffer limits | Covers only off-by-one arithmetic/indexing. Does not cover boolean inversions or `None` dereferences. Many instances are functional bugs rather than security vulnerabilities. | Moderate (for off-by-one sub-type) | MITRE CWE-193 |
| | **CWE-476** | NULL Pointer Dereference | Captures unhandled access to attributes on `None` in Python | Application dereferences an object pointer/reference that it expects to be valid, but is NULL/None | In Python, causes unhandled `AttributeError: 'NoneType'` crash. Closely related to CWE-754 / CWE-252 (Unchecked Return Value). | Moderate (for `None` handling sub-type) | MITRE CWE-476 / CWE-754 |
| | **CWE-670** | Always-Incorrect Control Flow Implementation | Captures flawed conditional branching and boolean logic | Program control flow is implemented such that execution can never produce intended behavior | High-level Class weakness. Spans general non-security logic bugs that lack specific CVE identifiers. | Low to Moderate (broad class) | MITRE CWE-670 |
| **2. Input validation & sanitization** | **CWE-20** | Improper Input Validation | Captures missing or inadequate validation of incoming request data | Software receives input from upstream but fails to verify format, length, range, or expected attributes | Must NOT be conflated with downstream injection (CWE-89, CWE-22). CWE-20 applies to data constraint validation; injection flaws belong to specific sink CWEs. | High (for schema/type validation) | MITRE CWE-20 / NIST SP 800-53 |
| | **CWE-116** | Improper Encoding or Escaping of Output | Captures failure to encode or escape data before output generation | Software prepares structured message but fails to encode/escape special characters | Focuses on transformation/neutralization rather than format validation. | High (for sanitization/encoding) | MITRE CWE-116 |
| **3. SQL / ORM injection** | **CWE-89** | Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection') | Captures user-controlled string interpolation in raw SQL and ORM raw fragments | Software constructs all or part of an SQL command using external input without neutralizing syntax elements | Applies to both raw SQL and ORM raw query methods (SQLAlchemy `text()`). Does not apply to non-SQL stores. | High (authoritative standard) | MITRE CWE-89 / OWASP A03:2021 |
| | **CWE-943** | Improper Neutralization of Special Elements in Data Query Logic | Captures query logic manipulation in ORM/NoSQL abstract query builders | Software constructs queries for data stores using external input without neutralizing query logic syntax | Parent class of CWE-89. Useful if dataset includes NoSQL or object-query structure injection. | Moderate to High (parent class) | MITRE CWE-943 |
| **4. Path traversal / unsafe file operations** | **CWE-22** | Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal') | Captures file operations allowing directory escape (`../` or root paths) | Software constructs a pathname from external input without neutralizing traversal sequences | Specifically involves escaping the restricted directory. Overwriting files inside the allowed folder is CWE-73. | High (authoritative standard) | MITRE CWE-22 / OWASP A01:2021 |
| | **CWE-73** | External Control of File Name or Path | Captures allowing external input to dictate filename/destination | Software allows user input to control or influence file paths in filesystem operations | Can occur without traversal sequences (e.g. overwriting files within intended directory). | High | MITRE CWE-73 |
| | **CWE-434** | Unrestricted Upload of File with Dangerous Type | Captures file upload endpoints accepting executable/dangerous extensions | Software allows upload of dangerous file types that can be processed or executed by the system | Specific to file upload functionality. | High | MITRE CWE-434 |
| **5. Missing / broken authentication** | **CWE-306** | Missing Authentication for Critical Function | Captures API endpoints lacking authentication dependencies | System does not perform any authentication for functionality requiring provable identity | Endpoint completely lacks authentication checks. Distinct from flawed authentication logic. | High | MITRE CWE-306 / OWASP A07:2021 |
| | **CWE-287** | Improper Authentication | Captures flawed token verification, weak secrets, broken signature checks | System attempts authentication but implementation contains defects or bypasses | Mechanism exists but is flawed. Parent of CWE-347 (signature verification). | High | MITRE CWE-287 |
| **6. Missing / broken authorization** | **CWE-862** | Missing Authorization | Captures endpoints lacking resource ownership or permission checks (IDOR) | System does not perform authorization checks when an actor accesses a resource | Endpoint verifies who the user is (authenticated) but fails to verify if they can access that specific record. | High | MITRE CWE-862 / OWASP API1:2023 |
| | **CWE-639** | Authorization Bypass Through User-Controlled Key | Captures IDOR / BOLA where user modifies parameter/ID to access another's data | User-controllable key used directly to access a record without authorization verification | Specifically models BOLA / IDOR in REST APIs (FastAPI/Flask route parameters). | High | MITRE CWE-639 |
| | **CWE-863** | Incorrect Authorization | Captures authorization logic bugs (wrong boolean conditions, role confusion) | System performs an authorization check, but the check contains flawed logic | Check exists but evaluates incorrectly. | High | MITRE CWE-863 |

---

## 5. Ambiguities & Boundary Cases

### 1. Functional Correctness Defects vs. Security Weaknesses in Category 1
- **The Ambiguity**: Category 1 ("Boundary / conditional logic") combines off-by-one calculations, boolean operator errors, and Python `NoneType` attribute errors.
- **Evidence Finding**: While MITRE maintains CWE entries for these mechanisms (CWE-193, CWE-480, CWE-476, CWE-670), in Python web applications, they rarely represent exploitable security vulnerabilities. Instead, they represent **reliability, data integrity, and functional logic defects** (e.g., incorrect financial totals, unhandled exceptions leading to HTTP 500, pagination off by 1).
- **Thesis Impact**: If the AI Code Auditor benchmark evaluates *both* functional software bugs and security vulnerabilities, Category 1 is a critical functional category. However, if the benchmark is strictly evaluated against security vulnerability databases (CVE/NVD), Category 1 cases will lack official CVE mappings unless they directly compromise security boundaries.
- **Status**: `Awaiting Student & Supervisor Decision`.

### 2. Upstream Input Validation (CWE-20) vs. Downstream Injections (CWE-89, CWE-22)
- **The Ambiguity**: When an unvalidated input parameter results in SQL injection or path traversal, should the defect be labeled as CWE-20, CWE-89, or both?
- **Evidence Finding**: MITRE official documentation explicitly states that CWE-20 is a root-cause contributing factor, whereas the primary vulnerability is the downstream injection weakness (CWE-89 or CWE-22).
- **Thesis Guidance**: In dataset annotation, reserve CWE-20 for defects where input validation *itself* is the primary missing requirement (e.g., negative price, string in integer field, invalid email format, payload size limits) that does not directly trigger an interpreter injection.

### 3. ORM Query Handling (CWE-89 vs. CWE-943)
- **The Ambiguity**: Does using an ORM like SQLAlchemy reclassify an injection bug from CWE-89 to CWE-943?
- **Evidence Finding**: In Python web applications, ORMs compile to SQL dialects. When raw user strings are concatenated into `text()` clauses or raw SQL queries, the underlying weakness remains **CWE-89**. CWE-943 should be reserved for NoSQL or object query languages where SQL is not the target interpreter.

### 4. Granularity of Authorization Mappings (CWE-285 vs. CWE-862 / CWE-639)
- **The Ambiguity**: Should authorization bugs be labeled with umbrella CWE-285 (Improper Authorization)?
- **Evidence Finding**: MITRE explicitly classifies CWE-285 as "Discouraged" for mapping real-world defects. The research recommends using **CWE-862** (Missing Authorization) and **CWE-639** (User-Controlled Key / IDOR / BOLA) for clear, granular ground truth.

---

## 6. Evidence Limitations & Gaps
1. **No Single Universal CWE for Category 1**: There is no authoritative single CWE that unifies off-by-one errors, conditional logic flaws, and `None` dereferences. They belong to separate branches of the MITRE hierarchy (CWE-682 Calculation vs. CWE-710 Coding Practices vs. CWE-691 Control Flow).
2. **Framework-Specific Idioms**: In FastAPI, input validation is declarative via Pydantic (`BaseModel`, `Field`, `Annotated`), and authentication/authorization is typically implemented via FastAPI's dependency injection system (`Depends()`). In Flask, validation and authentication are typically implemented via decorators (`@login_required`), Marshmallow schemas, or manual request parsing. Mapping schemas must accommodate both declarative and procedural enforcement patterns.
3. **No Numerical Weights or Scoring**: This research provides qualitative and taxonomic evidence only. No synthetic scores, weights, or rankings are assigned to any candidate CWE.

---

## 7. Official Source References

1. **MITRE Corporation — Common Weakness Enumeration (CWE)**
   - *CWE-20*: Improper Input Validation — `https://cwe.mitre.org/data/definitions/20.html`
   - *CWE-22*: Improper Limitation of a Pathname to a Restricted Directory ('Path Traversal') — `https://cwe.mitre.org/data/definitions/22.html`
   - *CWE-73*: External Control of File Name or Path — `https://cwe.mitre.org/data/definitions/73.html`
   - *CWE-89*: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection') — `https://cwe.mitre.org/data/definitions/89.html`
   - *CWE-116*: Improper Encoding or Escaping of Output — `https://cwe.mitre.org/data/definitions/116.html`
   - *CWE-193*: Off-by-one Error — `https://cwe.mitre.org/data/definitions/193.html`
   - *CWE-285*: Improper Authorization (Discouraged) — `https://cwe.mitre.org/data/definitions/285.html`
   - *CWE-287*: Improper Authentication — `https://cwe.mitre.org/data/definitions/287.html`
   - *CWE-306*: Missing Authentication for Critical Function — `https://cwe.mitre.org/data/definitions/306.html`
   - *CWE-434*: Unrestricted Upload of File with Dangerous Type — `https://cwe.mitre.org/data/definitions/434.html`
   - *CWE-476*: NULL Pointer Dereference — `https://cwe.mitre.org/data/definitions/476.html`
   - *CWE-639*: Authorization Bypass Through User-Controlled Key — `https://cwe.mitre.org/data/definitions/639.html`
   - *CWE-670*: Always-Incorrect Control Flow Implementation — `https://cwe.mitre.org/data/definitions/670.html`
   - *CWE-862*: Missing Authorization — `https://cwe.mitre.org/data/definitions/862.html`
   - *CWE-863*: Incorrect Authorization — `https://cwe.mitre.org/data/definitions/863.html`
   - *CWE-943*: Improper Neutralization of Special Elements in Data Query Logic — `https://cwe.mitre.org/data/definitions/943.html`

2. **OWASP Foundation**
   - *OWASP Top 10 (2021)*: A01 Broken Access Control, A03 Injection, A07 Identification and Authentication Failures.
   - *OWASP API Security Top 10 (2023)*: API1 Broken Object Level Authorization (BOLA), API2 Broken Authentication, API5 Broken Function Level Authorization.

3. **National Institute of Standards and Technology (NIST)**
   - *NIST Special Publication 800-53 (Rev. 5)*: Security and Privacy Controls for Information Systems and Organizations (Access Control AC-3/AC-6, System and Information Integrity SI-10).

---

## 8. Governance Statement

> **IMPORTANT**: The candidate CWE mappings and taxonomic boundaries presented in this document represent factual, source-backed evidence gathered from official standards bodies. **They do not constitute a final thesis decision.**
>
> The final taxonomy selection, inclusion/exclusion of functional non-security categories, and benchmark ground-truth labels remain strictly under the authority of the student (**Bui Van Khai**) and thesis supervisor (**ThS. Tran Thi Hong Yen**).
