# R3 Summary: CWE Taxonomy & Target Defect Classification

## 1. Overview & Context

In automated code auditing for Python web backends (FastAPI and Flask), defining unambiguous defect categories and aligning them with authoritative industry standards (MITRE Common Weakness Enumeration - CWE) is critical for reproducible evaluation.

This document summarizes the research and formal alignment of the **6 target defect categories** established in the thesis, identifying primary and candidate CWE mappings, structural boundaries, and taxonomy governance rules.

---

## 2. The 6 Locked Defect Categories

| Category ID | Category Name | Primary Focus | Key Subtypes |
| :---: | :--- | :--- | :--- |
| **1** | **Boundary / Conditional / Logic** | Program logic flow, boundary limits, and null handling. | Off-by-one loops/slicing, inverted boolean conditions, unhandled `None` attribute access (`AttributeError`). |
| **2** | **Input Validation & Sanitization** | Structural, type, and format validation of incoming untrusted data. | Missing Pydantic/Marshmallow schema checks, unvalidated parameter ranges/types, missing output escaping. |
| **3** | **SQL / ORM Injection** | Unsanitized dynamic query construction in relational databases. | Raw SQL string interpolation, raw query fragments in ORMs (e.g. SQLAlchemy `session.execute(text(...))`). |
| **4** | **Path Traversal / Unsafe File Ops** | Unrestricted filesystem operations and directory boundary escapes. | Path traversal via `../` or root injection (`os.path.join` discard), arbitrary file overwrite, unsafe file uploads. |
| **5** | **Missing / Broken Authentication** | Verification of user/client identity and credential validity. | Unprotected API endpoints missing auth dependencies, unverified JWT signatures (`verify_signature=False`), hardcoded secrets. |
| **6** | **Missing / Broken Authorization** | Enforcement of permissions, resource access rights, and tenant boundaries. | Missing ownership checks on user-controlled IDs (IDOR/BOLA), flawed role comparison, vertical privilege escalation. |

---

## 3. Authoritative CWE Candidate Mapping

Based on MITRE CWE definitions and Python web development characteristics, the candidate mappings are structured as follows:

| Category | Candidate CWE | CWE Name | Level | Scope & Application in Python Web Apps |
| :--- | :--- | :--- | :--- | :--- |
| **1. Boundary / Logic** | **CWE-193** | Off-by-one Error | Base | Indexing calculation, slice boundaries (`[:n]` vs `[:n+1]`), loop limits. |
| | **CWE-476** | NULL Pointer Dereference | Base | Unchecked `None` returns causing `AttributeError: 'NoneType' object has no attribute`. |
| | **CWE-670** | Always-Incorrect Control Flow Implementation | Class | Flawed branching logic, inverted conditionals, unreachable or flawed execution flow. |
| | **CWE-754** | Improper Check for Unusual Conditions | Class | Missing exception checks or unchecked function return values. |
| **2. Validation** | **CWE-20** | Improper Input Validation | Class | Request bodies, query parameters, or headers missing type/format/range constraints. |
| | **CWE-116** | Improper Encoding or Escaping of Output | Class | Failure to encode/escape output strings before passing to downstream renderers. |
| | **CWE-1287** | Improper Validation of Specified Type of Input | Base | Failure to enforce expected types (e.g. string accepted where integer required). |
| **3. SQL / ORM Injection**| **CWE-89** | SQL Injection | Base | External input interpolated into SQL queries or ORM raw clauses. |
| | **CWE-943** | Improper Neutralization in Data Query Logic | Class | Abstract query structure manipulation (ORM query builders, NoSQL stores). |
| **4. Path Traversal** | **CWE-22** | Path Traversal | Base | Input containing traversal sequences (`../`, absolute paths) escaping root directories. |
| | **CWE-73** | External Control of File Name or Path | Base | User input controls destination filename, even within allowable directories. |
| | **CWE-434** | Unrestricted Upload of File with Dangerous Type | Base | Uploading executable or script files (`.py`, `.sh`, `.html`) to web-accessible locations. |
| **5. Authentication** | **CWE-306** | Missing Authentication for Critical Function | Base | Sensitive endpoints completely omitting authentication checks. |
| | **CWE-287** | Improper Authentication | Class | Flawed authentication implementation (weak tokens, broken token validation logic). |
| | **CWE-347** | Improper Verification of Cryptographic Signature | Base | JWT or HMAC verification disabled or improperly handled (`verify_signature=False`). |
| **6. Authorization** | **CWE-862** | Missing Authorization | Base | Endpoint completely lacks access-control check after authentication. |
| | **CWE-863** | Incorrect Authorization | Base | Authorization check exists but contains flawed logic (e.g. role check inverted). |
| | **CWE-639** | Authorization Bypass Through User-Controlled Key | Base | IDOR / BOLA: accessing records of other users via manipulable IDs in URLs or bodies. |

---

## 4. Key Taxonomic Boundaries & Disambiguation Rules

### 4.1 Input Validation (CWE-20) vs. Downstream Injections (CWE-89, CWE-22)
- **Boundary**: Input validation checks syntax, structure, type, and range at the API boundary (e.g., Pydantic schema validation). Injection occurs when untrusted data crosses a structural boundary into an interpreter or sink.
- **Rule**: If a defect is missing schema validation, it belongs to Category 2 (CWE-20). If untrusted data directly reaches an SQL query or filesystem call, the defect is classified primarily as Category 3 (CWE-89) or Category 4 (CWE-22), with CWE-20 acting only as an upstream contributing factor.

### 4.2 Authentication (AuthN) vs. Authorization (AuthZ)
- **Authentication (Category 5)**: Proves **who the user is** (identity verification). Failures include missing token checks (CWE-306) or bypassed signature verification (CWE-347).
- **Authorization (Category 6)**: Determines **what the user is permitted to do** (access rights). Failures include accessing another tenant's data via object ID (CWE-639 / BOLA) or performing admin actions without administrative roles (CWE-862 / CWE-863).

### 4.3 Deprecation of Abstract Umbrella CWE-285
- MITRE designates CWE-285 (*Improper Authorization*) as a **Discouraged** mapping because it is overly broad.
- In this thesis, Category 6 defects are mapped specifically to concrete base-level weaknesses: **CWE-862** (missing check), **CWE-863** (flawed check), or **CWE-639** (IDOR/BOLA).

### 4.4 Category 1 Dual-Nature: Functional vs. Security Defects
- Boundary and logic errors often manifest as functional bugs (HTTP 500 exceptions, wrong calculations, broken pagination) rather than exploitable security vulnerabilities.
- **Solution**: To preserve the 6-category structure without forcing non-security bugs into inappropriate security categories, Category 1 cases are annotated with an orthogonal metadata attribute:
  $$\text{impact} \in \{\text{"functional"}, \text{"security"}\}$$
  This allows benchmark reporting to isolate functional correctness from security evaluations cleanly.

### 4.5 Multi-Label Representation & Pre-Declared Alternative Sets
- A primary CWE is designated for every defect case.
- When a defect exhibits dual aspects (e.g. an unvalidated parameter leading to an SQL injection, or a token parsing flaw), up to two alternative CWEs may be pre-declared in `alternative_cwe_set`.
- Evaluation matching accepts findings matching either the primary CWE or pre-declared alternative CWEs. If multi-label scoring introduces ambiguity, the evaluation deterministically falls back to the primary CWE.
