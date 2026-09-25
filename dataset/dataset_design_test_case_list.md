# Benchmark Dataset Design & Test Case List Specification

## Document Information
- **Document Version**: Version 1.1 — Test-Case Construction Workflow & Candidate Ingestion Schema Defined
- **Date**: 2026-09-25
- **Project**: Automated Code Review and Bug Detection System (AI Code Auditor)
- **Student**: Bùi Vạn Khải (MSSV: 24520719)
- **Supervisor**: ThS. Tran Thi Hong Yen
- **Institution**: University of Information Technology — VNU-HCM
- **Status**: VALIDATED DELIVERABLE — Benchmark dataset design, schema, locked 6-category taxonomy, locked ±10 lines matching tolerance, candidate-ingestion schema, and test-case construction workflow finalized. Candidate inventory = 0; benchmark harvesting ready to begin.

---

## 1. Dataset Purpose & Evaluation Context

The purpose of this benchmark dataset is to provide an objective, repeatable, and ground-truth-validated test bed for evaluating automated Pull Request auditing performance across the four experimental configurations planned in the thesis:

- **Configuration A**: Deterministic static analysis alone (Ruff + Semgrep).
- **Configuration B**: Heuristic LLM review alone (isolated diff + single-file context).
- **Configuration C**: Hybrid review (Static + LLM) without repository-wide context.
- **Configuration D**: Hybrid review (Static + LLM) augmented with repository-level context retrieval (AST graphs + pgvector embeddings).

> **Important Boundary**: The benchmark dataset is an **evaluation artifact**, not a component of the runtime production system. It is curated exclusively to benchmark detection accuracy (Precision, Recall, F1, FPR) and operational efficiency (latency, token consumption, cost).

---

## 2. Baseline Dataset Targets

The benchmark dataset adheres to the quantitative targets and working balance rules established for the thesis:

- **Total Cases Target**: **Minimum 100 cases** (floor baseline; no fixed ceiling at this stage).
- **Balance Target**: **50 Buggy PRs / 50 Clean PRs** (50% defect prevalence baseline target).
- **Category Representation Balance**: Planned category representation shall be approximately balanced, with category counts remaining within **10 cases of one another** where practical across the six defect classes.
- **Complexity Mix**: Dataset shall contain both single-file and cross-file cases, with the final distribution determined during dataset construction and documented before evaluation (with an initial planning target of ~50% single-file / ~50% cross-file).
- **Target Language & Frameworks**: Python targeting small-to-medium web applications (FastAPI and Flask) (validated implementation choice).

---

## 3. Development vs. Test Split Protocol

To prevent evaluation bias, data snooping, and prompt overfitting, the dataset is formally partitioned into a Development set and a Test set:

- **Split Ratio**: **30% Development Set / 70% Test Set**
  - **Development Set (30 cases)**: 15 Buggy / 15 Clean. Used for prompt template refinement, static rule tuning, context slicing heuristics, and initial pipeline debugging.
  - **Test Set (70 cases)**: 35 Buggy / 35 Clean. Strictly locked and held out. Used exclusively for final benchmarking across Configurations A, B, C, and D.

### Split Rationale & Protocol
1. **Stratified Sampling**: Both the Development and Test sets are stratified proportionally across the six working bug categories and the single-file vs. cross-file complexity tiers.
2. **Repository-Family Grouping**: All PR cases sourced from the same underlying software repository are assigned to the same partition (either Dev or Test, never split across both). This prevents repository-specific memorization or leakage.
3. **Locking Protocol**: Once the test cases are curated and verified against ground truth, the Test Set is strictly locked. No prompt modifications or parameter adjustments are permitted after unblinding the test set.

---

## 4. Case Metadata Schema

Every benchmark case is annotated with a comprehensive 16-field metadata schema ensuring full experimental reproducibility:

| # | Field Name | Data Type | Requirement | Description & Format |
|---|---|---|---|---|
| 1 | `case_id` | String | Required | Unique identifier (e.g., `PR-BUG-001`, `PR-CLN-001`). |
| 2 | `repository` | String | Required | Upstream GitHub repository identifier (`owner/repo`). |
| 3 | `PR_or_commit` | String | Required | PR number or commit SHA of the audited change. |
| 4 | `language` | String | Required | Target language and version (e.g., `Python 3.11`). |
| 5 | `bug_class` | Integer | Required | Working bug category ID (1 to 6 for buggy; 0 for clean). |
| 6 | `CWE` | String | Required | Primary CWE mapping (plus up to 2 secondary CWEs if necessary/justified, e.g., `CWE-89`; pre-declared alternative CWEs documented per case). |
| 7 | `changed_files` | List[String] | Required | List of all relative file paths modified in the PR diff. |
| 8 | `ground_truth_files` | List[String] | Required | Specific file path(s) where the defect is located (empty for clean). |
| 9 | `ground_truth_line_range` | String | Required | 1-indexed line range of the defect in `head` state (e.g., `45-52`). |
| 10 | `bug_description` | String | Required | Concise explanation of the flaw, trigger condition, and impact. |
| 11 | `pre_fix` | String (Git SHA) | Required | Commit SHA containing the defect (or base state for clean). |
| 12 | `post_fix` | String (Git SHA) | Required | Commit SHA containing the verified remediation. |
| 13 | `minimal_diff` | Text (Patch) | Required | Unified diff patch of the change being audited. |
| 14 | `verification_test` | String | Required | Identifier/command of the automated test reproducing the defect. |
| 15 | `expected_detection` | List[String] | Required | Configurations expected to detect the defect (e.g., `[Config_D]`). |
| 16 | `impact` | String | Required for Cat 1 | Orthogonal impact classification (`functional` \| `security`) distinguishing functional correctness from security logic flaws. |

> **Note on Evaluation Matching**: The metadata field `ground_truth_line_range` strictly records the 1-indexed defect line coordinates in the `head` revision. The authoritative evaluation matching rule uses a locked tolerance window of **±10 lines** around the ground-truth range, alongside exact normalized file matching and category / pre-declared alternative CWE matching (see Section 14, Section 15, and FR-09).

---

## 5. Locked Bug Category Structure & CWE Taxonomy Alignment

The benchmark evaluates defect detection across exactly six locked categories. The table below records their stable IDs, locked titles, candidate CWE mappings established during research (`CWE_taxonomy.md`), and their formal methodology status:

| Category ID | Locked Category Title | Methodology Status | Research Candidate Mapping (`CWE_taxonomy.md`) | Scope & Notes |
|:---:|:---|:---:|:---|:---|
| **1** | **Boundary / conditional logic** | `LOCKED METHODOLOGY` | CWE-193 (Off-by-one)<br>CWE-476 (NULL Dereference)<br>CWE-754 (Exceptional Conditions)<br>CWE-670 (Control Flow) | Off-by-one slicing, unhandled Python `NoneType` attribute access, inverted boolean logic. Annotated with orthogonal `impact = functional \| security` attribute. |
| **2** | **Input validation & sanitization** | `LOCKED METHODOLOGY` | CWE-20 (Improper Input Validation)<br>CWE-116 (Improper Encoding/Escaping)<br>CWE-1287 (Type Validation) | Missing request body/schema validation (Pydantic/Marshmallow), unvalidated ranges, unescaped strings. |
| **3** | **SQL / ORM injection** | `LOCKED METHODOLOGY` | CWE-89 (SQL Injection)<br>CWE-943 (Data Query Logic) | Unsanitized string formatting in raw SQL execution or ORM raw clauses (SQLAlchemy `session.execute(text(...))`). |
| **4** | **Path traversal / unsafe file ops** | `LOCKED METHODOLOGY` | CWE-22 (Path Traversal)<br>CWE-73 (External Control of Path)<br>CWE-434 (Unrestricted File Upload) | Directory escape via `../`, arbitrary file overwrite via unvalidated filename, unsafe file extension uploads. |
| **5** | **Missing / broken authentication** | `LOCKED METHODOLOGY` | CWE-306 (Missing Authentication)<br>CWE-287 (Improper Authentication)<br>CWE-347 (Improper Signature Check) | Unprotected sensitive API endpoints, unverified JWT signatures (`verify_signature=False`), hardcoded secrets. |
| **6** | **Missing / broken authorization** | `LOCKED METHODOLOGY` | CWE-862 (Missing Authorization)<br>CWE-639 (User-Controlled Key / BOLA)<br>CWE-863 (Incorrect Authorization) | Missing resource ownership checks (IDOR / BOLA), vertical privilege escalation, flawed role comparison logic. |

> **Final / Validated Methodology Decisions**:
> 1. **Initial Locked Taxonomy**: Exactly six categories are the locked initial taxonomy for the thesis benchmark. If dataset construction naturally reveals a meaningful defect type that does not fit the existing taxonomy, expansion by up to two additional top-level categories is permitted, provided the addition is justified and documented. No unnecessary taxonomy expansion should occur.
> 2. **CWE Multi-Label Representation & Fallback Policy**: A test case may contain multiple CWE labels when necessary for accurate characterization of the defect (maximum 3 CWE labels per case; multi-CWE cases should remain uncommon and justified). A case may use a single primary CWE when that is sufficient. If retaining multiple CWE labels would create disproportionate evaluation complexity or prevent a reliable/reproducible scoring mechanism, use a single primary CWE instead.
> 3. **Category 1 Impact Attribute**: Rather than creating a seventh category, Category 1 cases include an orthogonal `impact = functional | security` attribute in metadata. This preserves the 6-category structure while enabling evaluation reports to distinguish general functional correctness defects from security-impacting logic flaws.

---

## 6. Ground-Truth Verification Rule & 10-Point Acceptance Gate

To maintain rigorous scientific validity, **no dataset case counts as ground truth based on tool or LLM assertion alone**. Every candidate case must satisfy an auditable chain of technical evidence:

```text
[Buggy Commit / State] 
          ↓ 
[Documented Defect Report / Advisory]
          ↓ 
[Automated Reproducer Test (Fails on Buggy Commit)]
          ↓ 
[Fixed Commit / Remediation Patch]
          ↓ 
[Post-Fix Verification (Reproducer Test Passes)]
```

### The 10-Point Ground-Truth Acceptance Checklist
A candidate case shall NOT be accepted into the benchmark unless all 10 conditions are satisfied (or explicitly justified under supervisor sign-off for structural limitations):

1. **Identifiable Buggy State**: The pre-fix repository commit SHA or tree state containing the flaw is deterministically identified.
2. **Documented Defect Evidence**: The vulnerability or bug is directly evidenced by an issue report, security advisory (GHSA/CVE/OSV), commit message, or pull request description.
3. **Identifiable Affected Locus**: The affected file path(s) and specific line coordinates in the `head` revision are deterministically known.
4. **Reproducer or Verification Test**: An executable test case (pytest/unittest) reproducing the defect exists or can be reliably constructed.
5. **Identifiable Fixed State**: The post-fix repository commit SHA applying the remediation is deterministically identified.
6. **Verified Fix**: The reproducer test deterministically fails on the buggy commit and passes on the fixed commit.
7. **Justified Category Assignment**: The defect strictly aligns with one of the six locked bug categories.
8. **Justified CWE Assignment**: Primary CWE (and up to 2 secondary CWEs where justified) is grounded in primary evidence; acceptable alternative CWE sets are pre-declared before evaluation.
9. **Within Thesis Scope**: The target repository is a Python application (FastAPI/Flask preferred) and falls within small-to-medium PR complexity bounds.
10. **Non-Duplicate**: The case represents an independent defect and is not a duplicate of an existing benchmark entry.

### Evidence Quality Classification Levels
Every ingested candidate is evaluated and assigned one of three quality levels:
- **Level A — Fully Verified**: Complete end-to-end evidence chain (`buggy commit → documented defect → reproducer test → fixed commit → verified fix`). Automatically eligible for primary benchmark inclusion upon passing deduplication.
- **Level B — Strong Evidence**: Primary repository evidence with a minor documentation gap (e.g., passing reproducer and verified patch, but issue discussion was informal or commit message lacked issue tracker link). Requires explicit documented justification to enter the benchmark.
- **Level C — Discovery Only**: Defect mentioned in an advisory or issue without an isolated reproducer or verifiable commit. Cannot enter the benchmark without further technical reconstruction.

---

## 7. Data Sourcing Strategy & 5-Tier Source Hierarchy

The dataset curation protocol enforces a strict 5-tier evidence hierarchy, prioritizing natural real-world defects over synthetic generation:

### 5-Tier Evidence Source Hierarchy
| Tier | Source Category | Description & Role | Verification Obligation |
|:---:|:---|:---|:---|
| **Tier 1** | **Primary Ground-Truth Evidence** | The actual target software repository and its native git history (buggy commit, issue/PR discussion, test suite, fixed commit). Authoritative technical ground truth. | Primary source of truth. All accepted cases must validate against Tier 1 artifacts. |
| **Tier 2** | **Structured Real-Bug Datasets** | Curated collections of real Python defects (BugsInPy, SWE-bench, verified vulnerability collections). | Discovery/indexing sources. Metadata alone cannot be trusted; underlying git repo and reproducer must be independently validated. |
| **Tier 3** | **Security Advisory Databases** | Authoritative vulnerability registries (GitHub Advisory Database / GHSA, OSV, PyPI/PyPA security advisories). | Discovery/indexing sources. Must be traced back to affected repository commit, vulnerable code lines, and reproducer tests. |
| **Tier 4** | **Controlled Security Benchmarks** | Controlled benchmarks (OWASP Benchmark, RealVuln). Used for controlled rule calibration and methodological reference. | Must be explicitly labeled as controlled benchmarks; deliberately injected flaws must be distinguished from organic bugs. |
| **Tier 5** | **Synthetic Defect Generation** | Controlled synthetic synthesis (SWE-smith). Used strictly as a last resort to fill coverage gaps in underrepresented categories. | Must be explicitly labeled (`real_or_synthetic = synthetic`), embedded in realistic multi-file web scaffold, and pass full test chain. |

### Source-Specific Handling Protocols
- **BugsInPy**: Used as a structured Python bug source. The verification process checks out the actual repository state, confirms the buggy/fixed commits, and executes the isolated pytest test suite.
- **SWE-bench**: Used as a source of GitHub pull requests solving real issues. The verification process inspects the original repository, verifies the issue report and PR diff, and executes the fail-to-pass test suite.
- **Security Advisories (GHSA / OSV / PyPI)**: Used to discover real-world security vulnerabilities. Each advisory must be traced to the upstream repository, isolating the vulnerable commit, the security patch commit, and reproduction test fixtures.
- **OWASP Benchmark**: Handled strictly as a controlled benchmark. Used for deterministic rule calibration, keeping synthetic and organic flaws separate.
- **SWE-smith**: Invoked only after Tier 1–3 sources have been systematically searched and specific high-risk categories (e.g., multi-file BOLA/IDOR or subtle JWT signature verification bypasses in FastAPI) lack sufficient samples.
- **No Rigid Percentage Quota**: Real-world, verifiable bugs are preferred. Synthetic cases may be used strictly to fill coverage gaps in underrepresented categories. There is no rigid real/synthetic percentage quota, while maintaining the minimum 100-case floor and category counts remaining within 10 cases of one another where practical.

### Methodological Literature Reference: RealVuln
- **Role**: Methodological reference for benchmark construction, defect categorization, and matching rule design.
- **Provenance & Conflict-of-Interest Caveat**: RealVuln is a recent academic preprint (arXiv:2604.13764, April 2026) developed in association with Kolega Labs / Kolega.Dev, whose commercial scanner is itself benchmarked. It is not an established, neutral, peer-reviewed, or universally validated industry standard. It does not prove that our methodology is correct, nor was our methodology derived from it.
- **Primary Source & Verified Scorer Implementation**:
  - **Repository**: [https://github.com/kolega-ai/Real-Vuln-Benchmark](https://github.com/kolega-ai/Real-Vuln-Benchmark)
  - **Implementation Reference**: Documented **Matching & Scoring / Finding Matching** implementation in [`scorer/matcher.py`](https://github.com/kolega-ai/Real-Vuln-Benchmark/blob/main/scorer/matcher.py).
  - **Verified Technical Details**:
    - Normalized file-path matching;
    - CWE matching through the ground truth's acceptable CWE set;
    - Line proximity within a ±10-line window around the ground-truth line range, corresponding to `[start_line - 10, end_line + 10]`;
    - One-to-one ground-truth consumption;
    - Unmatched additional findings counted as FP.
- **Methodological Relevance**: RealVuln is a recent methodological precedent whose published scorer uses a file + CWE + line proximity within a ±10-line window around the ground-truth line range (`[start_line - 10, end_line + 10]`) matching strategy with one-to-one ground-truth matching. It does not "prove" our matching tolerance or serve as an authoritative standard, but provides checkable contemporary literature precedent for proximity-based evaluation of security scanners on real-world code.

---

## 8. Role of Tooling in Benchmark Construction (GPT Researcher Operational Rules)

To prevent LLM hallucinations or plausible-sounding summaries from corrupting ground truth, strict boundaries govern automated research tooling:

> **Operational Rule**: **GPT Researcher is a candidate-discovery and research-assistance tool, not a ground-truth authority.**

### Permitted Research Tooling Functions
- Executing broad web and GitHub queries to discover candidate bug-fixing PRs, issues, and security advisories.
- Locating repository URLs, commit SHAs, and patch diffs across open-source FastAPI/Flask repositories.
- Extracting candidate source links and populating the preliminary intake fields of the Candidate Case Record.
- Identifying initial candidate CWE alignments from advisory text for human/executor evaluation.
- Producing a candidate queue for human and repository-executor verification.

### Strictly Prohibited Actions
- Declaring a candidate case valid, verified, or accepted into the benchmark.
- Establishing ground-truth line coordinates, hunk boundaries, or defect locus.
- Inventing or asserting reproducer tests, test commands, or fixed commits.
- Inventing CWE mappings without verifiable primary source code evidence.
- Inferring that a defect existed merely because an LLM states that code looks buggy or plausible.

Every candidate case produced by GPT Researcher must undergo independent technical verification by the repository executor (Antigravity) and the student against Tier 1 primary repository evidence.

---

## 9. Candidate-Ingestion Schema & Intake Staging

The dataset pipeline maintains a strict operational separation between **candidate intake records** (in-flight staging) and **accepted benchmark cases** (locked evaluation dataset).

### Relationship to the 16-Field Case Metadata Schema
- The authoritative **16-field Case Metadata Schema** (defined in Section 4) represents the locked schema for finalized, accepted benchmark cases.
- The **Candidate Case Record Schema** (below) contains additional provenance, staging, and audit metadata required during the discovery and verification lifecycle. When a candidate achieves `eligibility_status = ACCEPTED`, its fields map directly to the 16-field schema.

### Candidate Case Record Schema (44 Staging Fields across 7 Logical Groups)

| # | Field Name | Data Type | Requirement | Description & Allowed Values |
|---|---|---|---|---|
| **Group 1** | **Discovery Fields** | | | |
| 1 | `candidate_id` | String | Required | Unique staging identifier (e.g., `CAND-001`, `CAND-042`). |
| 2 | `source_type` | String | Required | Origin: `BugsInPy` \| `SWE-bench` \| `GHSA` \| `OSV` \| `GitHub_PR` \| `SWE-smith`. |
| 3 | `source_name` | String | Required | Name of the source collection or discovery query. |
| 4 | `source_url` | String | Required | URL to the discovery record or advisory. |
| 5 | `repository` | String | Required | Upstream GitHub repository identifier (`owner/repo`). |
| 6 | `repository_url` | String | Required | Full HTTPS URL to the GitHub repository. |
| 7 | `issue_url` | String | Optional | URL to the tracked bug report / issue. |
| 8 | `pull_request_url` | String | Optional | URL to the original bug-fixing pull request. |
| 9 | `advisory_url` | String | Optional | URL to the security advisory (GHSA/CVE/OSV) if applicable. |
| 10 | `discovery_notes` | Text | Optional | Contextual notes on how the candidate was discovered. |
| 11 | `discovered_at` | String | Required | ISO 8601 timestamp of initial candidate extraction. |
| **Group 2** | **Version / Control Fields** | | | |
| 12 | `buggy_commit` | String | Required | Git commit SHA containing the verified defect. |
| 13 | `fixed_commit` | String | Required | Git commit SHA containing the verified patch. |
| 14 | `base_commit` | String | Optional | Base parent commit SHA of the audited pull request. |
| 15 | `commit_urls` | List[String] | Required | Direct URLs to the relevant commit diffs on GitHub. |
| **Group 3** | **Ground-Truth Evidence Fields** | | | |
| 16 | `bug_description` | Text | Required | Concise explanation of the flaw, trigger conditions, and impact. |
| 17 | `documented_defect_evidence` | Text | Required | Direct quote or reference link from issue/advisory detailing the defect. |
| 18 | `reproducer_test` | String | Required | Executable command or test file reproducing failure on buggy commit. |
| 19 | `verification_test` | String | Required | Executable command confirming test passes on fixed commit. |
| 20 | `fix_description` | Text | Required | Summary of technical remediation applied in the patch. |
| 21 | `verification_result` | Text | Required | Terminal output or log confirming fail-to-pass reproducer execution. |
| 22 | `ground_truth_verified` | Boolean | Required | `True` only when reproducer execution is confirmed. |
| **Group 4** | **Location Fields** | | | |
| 23 | `ground_truth_files` | List[String] | Required | List of relative file paths containing the defect locus. |
| 24 | `ground_truth_line_start` | Integer | Required | 1-indexed starting line number of defect in `head` revision. |
| 25 | `ground_truth_line_end` | Integer | Required | 1-indexed ending line number of defect in `head` revision. |
| 26 | `normalized_file_path` | String | Required | Canonical relative path stripped of local workspace prefixes. |
| 27 | `location_evidence` | Text | Required | Code snippet or diff hunk demonstrating the exact defect locus. Multi-region flaws explicitly record all constituent ranges. |
| **Group 5** | **Classification Fields** | | | |
| 28 | `bug_class` | Integer | Required | Working bug category ID (1 to 6; 0 for clean PRs). |
| 29 | `impact` | String | Required | `functional` \| `security` (mandatory for Category 1). |
| 30 | `cwe_labels` | List[String] | Required | List of up to 3 candidate CWE IDs (e.g., `["CWE-89"]`). |
| 31 | `primary_cwe` | String | Required | Single authoritative primary CWE ID (e.g., `"CWE-89"`). |
| 32 | `acceptable_alternative_cwes`| List[String] | Required | Pre-declared list of alternative CWEs acceptable during evaluation. |
| 33 | `classification_rationale` | Text | Required | Justification for assigned category, primary CWE, and alternatives. |
| **Group 6** | **Dataset-Control Fields** | | | |
| 34 | `real_or_synthetic` | String | Required | `real` \| `synthetic`. |
| 35 | `source_tier` | String | Required | `Tier_1` \| `Tier_2` \| `Tier_3` \| `Tier_4` \| `Tier_5`. |
| 36 | `category_balance_group` | String | Required | Category identifier used for quota balancing (`Cat_1` to `Cat_6`, `Clean`). |
| 37 | `duplicate_group` | String | Optional | Canonical cluster ID linking duplicate appearances across sources. |
| 38 | `split_group` | String | Required | `dev` \| `test` \| `unassigned`. |
| 39 | `quality_level` | String | Required | `Level_A` (Fully verified) \| `Level_B` (Strong evidence) \| `Level_C` (Discovery). |
| 40 | `eligibility_status` | String | Required | Ingestion status (see lifecycle state machine below). |
| 41 | `exclusion_reason` | String | Optional | Reason for rejection (empty if eligible or accepted). |
| **Group 7** | **Provenance & Audit Fields** | | | |
| 42 | `verifier_id` | String | Required | Identity of researcher / executor who verified the case. |
| 43 | `verified_at` | String | Required | ISO 8601 timestamp of verification. |
| 44 | `audit_notes` | Text | Optional | Specific audit notes regarding edge cases or structural limitations. |

---

## 10. Candidate Case Lifecycle, Quality Tiers & Deduplication Protocol

To prevent unverified web discoveries from leaking into the evaluation dataset, candidates traverse a formalized lifecycle gate:

### Candidate Lifecycle State Machine
```text
[DISCOVERED]  ── (Extracted from Tier 2/3/4 source or search query)
      ↓
[CANDIDATE]   ── (Basic repository, commit, and defect metadata recorded)
      ↓
[SOURCE VERIFIED] ── (Repository accessible; commit SHAs and diffs verified)
      ↓
[GROUND-TRUTH VERIFIED] ── (Reproducer executed; fail-to-pass confirmed; 10-point gate passed)
      ↓
[CLASSIFIED]  ── (Category 1–6 assigned; primary CWE and alternatives pre-declared)
      ↓
[DEDUPLICATED] ── (Cross-source check completed; duplicate cluster resolved)
      ↓
[ELIGIBLE]    ── (Meets all quality standards; pending dataset balance allocation)
      ↓
[ACCEPTED INTO BENCHMARK] ── (Assigned case_id PR-BUG-xxx / PR-CLN-xxx; mapped to 16-field schema)
```

### Terminal Rejection States
If a candidate fails any verification stage, it is immediately transitioned to one of the terminal rejection states:
- `REJECTED`: Fails basic technical standards or violates thesis boundaries.
- `DUPLICATE`: Represents an identical bug already ingested from another source.
- `INSUFFICIENT_EVIDENCE`: Lacks verifiable commit history, patch, or reproducible documentation.
- `OUT_OF_SCOPE`: Non-Python codebase, out-of-scope framework, or unmanageable diff complexity.
- `UNRESOLVED_CLASSIFICATION`: Defect cannot be definitively mapped to the 6 locked categories.
- `UNREPRODUCIBLE`: Automated test cannot reproduce failure in buggy commit or passes prematurely.

### Deduplication Protocol
1. **Cross-Source Defect Clustering**: A candidate is checked against all existing records using: (a) upstream repository full name (`owner/repo`), (b) commit SHA ranges, (c) issue/PR numbers, (d) CVE/GHSA identifiers, and (e) underlying defect locus and call stack.
2. **Canonical Case Selection**: When a bug appears in multiple sources (e.g., BugsInPy bug #12 is also indexed in SWE-bench and tracked under a GHSA advisory), it is merged into **one canonical benchmark case**. The record preserves references to all sources in `discovery_notes`, but only one `case_id` is created.
3. **No Artificial Inflation**: Multiple PRs refactoring or tweaking the same defect patch count as a single case.

### Case Provenance Requirements
Every accepted case must retain an auditable trail of primary URLs and commit hashes:
- Upstream GitHub repository URL.
- Direct commit diff URLs for `buggy_commit` and `fixed_commit`.
- Issue tracker URL or security advisory URL.
- Exact CLI command used to execute the reproducer test suite.
- Timestamped audit log of test verification.
Prose descriptions generated by LLMs are never accepted as primary provenance.

---

## 11. End-to-End Test Case Construction Workflow

The test case construction phase executes the following 8-step operational workflow to build the benchmark:

```text
Step 1: Candidate Discovery (GPT Researcher + Manual Repo Mining)
      ↓
Step 2: Source Verification (Verify Repository, Commit SHAs, Diff)
      ↓
Step 3: Bug/Fix Chain Reconstruction (Isolate Issue, Patch, Reproducer)
      ↓
Step 4: Ground-Truth Extraction (Extract Normalized Files, Line Ranges, CWEs)
      ↓
Step 5: Eligibility Check (10-Point Acceptance Gate & Quality Tiering)
      ↓
Step 6: Dataset Balancing (Category Quota & Real/Synthetic Balance Monitoring)
      ↓
Step 7: Benchmark Acceptance (Promote to ACCEPTED, Assign 16-Field Metadata)
      ↓
Step 8: Locked Split Assignment (Grouped Stratified 30% Dev / 70% Test Split)
```

- **Step 1 — Candidate Discovery**: Use GPT Researcher and targeted repository search to identify candidate bug-fixing commits across Python repositories (FastAPI/Flask preferred). Record candidates with `eligibility_status = DISCOVERED`.
- **Step 2 — Source Verification**: Clone the target repository or access GitHub API to verify that the commits exist, the diff is intact, and the repository builds. Update to `SOURCE_VERIFIED`.
- **Step 3 — Bug/Fix Chain Reconstruction**: Reconstruct the evidence chain: locate the issue description, check out `buggy_commit`, extract the reproducer test, apply `fixed_commit`, and confirm test execution. Update to `GROUND_TRUTH_VERIFIED`.
- **Step 4 — Ground-Truth Extraction**: Map the defect to its exact 1-indexed line coordinates in the `head` revision. Assign the primary bug category (1–6), impact attribute (`functional | security`), primary CWE, and pre-declare acceptable alternative CWEs. Update to `CLASSIFIED`.
- **Step 5 — Eligibility Check**: Validate the case against the 10-point Ground-Truth Acceptance Checklist. Assign Quality Level A or B (Level C rejected). Run deduplication against existing candidates. Update to `DEDUPLICATED` and `ELIGIBLE`.
- **Step 6 — Dataset Balancing**: Check current category balance (ensuring category counts remain within 10 cases of one another where practical) and maintain the floor of $\ge 100$ cases with appropriate single-file vs. cross-file complexity.
- **Step 7 — Benchmark Acceptance**: Assign formal benchmark `case_id` (`PR-BUG-xxx` or `PR-CLN-xxx`), map candidate fields to the 16-field Case Metadata Schema, and update status to `ACCEPTED INTO BENCHMARK`.
- **Step 8 — Locked Split Assignment**: Apply stratified 30% Dev / 70% Test partitioning grouped strictly by repository family to prevent data leakage. Once complete, lock the Test set.

---

## 12. First-Draft Case Allocation Plan (Planning Allocation Targets)

The following allocation plan represents the **planning targets** for achieving balanced coverage across the six categories and complexity tiers within the minimum 100-case baseline. The specific counts per category (8, 9, etc.) and complexity splits are planning targets for benchmark construction; category counts will remain within 10 cases of one another where practical:

| Planned Case Group | Baseline Target Count | Bug Category | Target Complexity Split | Primary Source Strategy | Ground-Truth Verification Requirement | Curation Status |
|:---|:---:|:---|:---|:---|:---|:---:|
| **GRP-01: Boundary Logic** | 8 (Draft Target) | Cat 1 (Boundary/Logic) | ~4 Single-File / ~4 Cross-File | BugsInPy / SWE-bench | Passing pytest reproducer | `TO BE SOURCED` |
| **GRP-02: Input Validation** | 9 (Draft Target) | Cat 2 (Input Validation) | ~5 Single-File / ~4 Cross-File | GitHub PR Mining (FastAPI/Pydantic) | Pydantic validation test | `TO BE SOURCED` |
| **GRP-03: SQL/ORM Injection** | 8 (Draft Target) | Cat 3 (SQL/ORM Injection) | ~4 Single-File / ~4 Cross-File | GitHub CVE Fixes / SWE-smith | SQL exploit test fixture | `TO BE SOURCED` |
| **GRP-04: Path Traversal** | 8 (Draft Target) | Cat 4 (Path Traversal) | ~4 Single-File / ~4 Cross-File | CVE Mining (Flask/FastAPI) | Filesystem escape reproducer | `TO BE SOURCED` |
| **GRP-05: Authentication** | 8 (Draft Target) | Cat 5 (Authentication) | ~4 Single-File / ~4 Cross-File | GitHub CVE Fixes / SWE-smith | Auth bypass HTTP test | `TO BE SOURCED` |
| **GRP-06: Authorization** | 9 (Draft Target) | Cat 6 (Authorization/BOLA) | ~4 Single-File / ~5 Cross-File | OWASP Benchmark / SWE-smith | BOLA tenant-isolation test | `TO BE SOURCED` |
| **GRP-07: Clean PRs (Single-File)** | 25 (Draft Target) | Cat 0 (Clean / Benign) | Single-File Diffs | Genuine Merged PRs (Refactor/Feature) | Full repo test suite passes | `TO BE SOURCED` |
| **GRP-08: Clean PRs (Cross-File)** | 25 (Draft Target) | Cat 0 (Clean / Benign) | Cross-File Diffs | Genuine Merged PRs (Multi-file Refactor) | Full repo test suite passes | `TO BE SOURCED` |
| **TOTAL** | **100 (Minimum Baseline Floor)** | **50 Buggy / 50 Clean (Target)** | **Balanced Single/Cross Mix** | **Real-world Preferred + Synthetic for Gaps** | **100% Verified Chains** | **Ready for Sourcing** |

> **Next Phase Transition**: No repository names, commit SHAs, or bug descriptions are fabricated in this specification. All cases remain designated as `TO BE SOURCED`, ready for the upcoming benchmark construction and case-harvesting phase.

---

## 13. Data Leakage & Partitioning Controls

To preserve strict evaluation integrity, the curation process enforces four anti-leakage controls:

1. **No Shared Defects Across Splits**: Different commits or variant patches addressing the same underlying bug cannot appear in both the Development and Test sets.
2. **Repository Boundary Isolation**: All PRs from a given repository (e.g., `tiangolo/fastapi` or `pallets/flask`) must reside entirely within either the Development split or the Test split.
3. **No Test Set Feedback**: Test set cases must never be inspected during prompt template authoring, few-shot prompt example selection, or context retrieval parameter tuning.
4. **Independent Random Repeatability**: Clean PRs are selected from commits immediately following or preceding the target repository's audited versions to match coding style and vocabulary, preventing the LLM from distinguishing clean vs. buggy cases based on coding style artifacts.

---

## 14. Evaluation Linkage & Metric Formulas

The dataset structure directly supports calculating formal academic evaluation metrics across all four experimental configurations:

### Detection Confusion Matrix & Authoritative Matching Rules

Under the authoritative project evaluation methodology, a predicted finding is classified as a **True Positive (TP)** if and only if ALL three matching conditions hold:

1. **File Match**: The normalized predicted file path exactly matches the normalized ground-truth file path (path-prefix differences are resolved during path normalization).
2. **Category / CWE Match**: The predicted category or CWE matches the ground-truth category/CWE, OR belongs to an explicitly pre-declared acceptable alternative CWE set associated with that ground-truth case. (Alternative CWE sets must be documented in ground truth prior to evaluation; no mappings may be invented post-hoc).
3. **Location Match**: The predicted line range overlaps the ground-truth line range, OR falls within the locked tolerance window around the ground-truth range.

#### Locked Tolerance Window
The final evaluation tolerance is locked to exactly **±10 lines** applied uniformly across Configurations A–D (±5 lines is removed as an unresolved alternative).

#### Matching Edge Cases & Protocol
- **Multi-line Findings**: Any line overlap with the ground-truth range satisfies the location component of the match.
- **One-to-One Matching**: Matching is strictly one-to-one. Once a ground-truth defect is matched by a prediction, it is consumed and cannot be matched again.
- **Multiple Predictions for One Defect / Unconsumed Predictions**: Any additional prediction that does not match an unconsumed ground-truth defect counts as a **False Positive (FP)**, even if another prediction from the same PR already matched the defect.
- **Clean Cases**: Any finding flagged on a clean PR is a **False Positive (FP)**. There is no distinct FP definition for clean vs. buggy PRs.
- **False Negatives**: A ground-truth defect on a buggy PR for which no valid matching prediction was emitted is a **False Negative (FN)**.
- **Secondary Diagnostic Metrics**: Exact line-match rate, distance between predicted and ground-truth line ranges, and category-only match rate may be recorded as diagnostic measurements, but must NOT alter the primary TP, FP, or FN counts.

#### Formal Classification Summary
- **True Positive (TP)**: An emitted prediction meeting all three matching conditions above against an unconsumed ground-truth defect.
- **False Positive (FP)**: 
  - Any finding flagged on a clean PR.
  - Any finding on a buggy PR that fails any of the three matching conditions, or represents an extra unconsumed prediction where the defect is already matched.
- **False Negative (FN)**: A ground-truth defect on a buggy PR for which no valid matching prediction was emitted.
- **True Negative (TN)**: A clean PR on which the auditor raises zero findings.

### Metric Formulas
$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}$$

$$\text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}$$

$$F_1 = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$

$$\text{False Positive Rate (FPR)} = \frac{\text{Clean PRs Flagged}}{\text{Total Clean PRs}}$$

> **Research Targets Note**: Precision $\ge 75\%$ and Recall $\ge 60\%$ are documented as non-binding research targets / empirical hypotheses, NOT hard acceptance criteria or pass/fail gates. They must not be used to declare the thesis successful or unsuccessful by themselves. Measured metrics will be evaluated empirically across Configurations A–D.

### Operational Resource Metrics
- **Median & P95 Latency**: Measured in seconds from PR intake to final finding aggregation.
- **Token Consumption**: Total prompt tokens and completion tokens consumed per PR audit.
- **Audit Cost**: Calculated directly from token volume using the published pricing of the active LLM API provider.

---

## 15. Dataset Governance, Current Inventory & Operational Task Status

The following table records the authoritative status of dataset methodological decisions, the construction workflow, and current benchmark inventory:

| Item | Validated Policy / Description | Methodology Status |
|---|---|:---:|
| **Initial Taxonomy Lock** | Locked to exactly 6 categories (Boundary/logic, Input validation, SQL/ORM injection, Path traversal, AuthN, AuthZ); maximum 2 additional categories permitted if naturally emerging during curation and justified. | `LOCKED FINAL METHODOLOGY` |
| **Sourcing & Balance Policy** | Minimum 100 cases (floor, no ceiling); real bugs preferred; synthetic used strictly to fill coverage gaps (no rigid percentage); category counts within 10 cases where practical. | `LOCKED FINAL METHODOLOGY` |
| **Category 1 Impact Attribute** | Preserves 6 categories without creating a 7th; Category 1 cases annotated with orthogonal `impact = functional \| security` attribute. | `LOCKED FINAL METHODOLOGY` |
| **Multi-label CWE Cases** | Maximum 3 CWE labels allowed when necessary and justified; fallback to single primary CWE if multi-label scoring creates disproportionate complexity. | `LOCKED FINAL METHODOLOGY` |
| **Finding Matching Semantics** | True Positive requires exact normalized file match, category/pre-declared alternative match, and overlap or locked ±10 lines tolerance. 1-to-1 matching; extra unmatched predictions = FP; clean findings = FP; unconsumed defect = FN. | `LOCKED EVALUATION RULE` |
| **Research Target Metrics** | Precision $\ge 75\%$ and Recall $\ge 60\%$ are research targets / empirical hypotheses, NOT hard acceptance criteria or pass/fail gates. | `VALIDATED RESEARCH HYPOTHESIS` |
| **Construction Workflow** | 8-step workflow (Candidate Discovery → Source Verification → Chain Reconstruction → Ground-Truth Extraction → Eligibility Check → Balancing → Acceptance → Locked Split). | `LOCKED OPERATIONAL WORKFLOW` |
| **Candidate Ingestion Schema** | 44 staging fields across 7 groups separating in-flight candidates from accepted cases. | `VALIDATED STAGING SCHEMA` |
| **Pilot Sourcing Validation** | Execution of a 10-case pilot batch (5 buggy, 5 clean) to validate the metadata extraction script and pytest harness before full scaling. | `OPERATIONAL EXECUTION TASK (Next Phase)` |
| **Benchmark Inventory** | Current candidate records: **0**. Current accepted benchmark cases: **0 / 100 Minimum**. | `BENCHMARK HARVESTING NOT YET STARTED` |

> **Project Benchmark Status Summary**:
> - **Evaluation Methodology**: `FINAL / VALIDATED`
> - **Test-Case Construction Workflow**: `DEFINED & AUDITABLE`
> - **Candidate Ingestion Schema**: `DEFINED`
> - **Candidate Ingestion Queue**: `0 Records`
> - **Accepted Benchmark Cases**: `0 / 100 Minimum`
> - **Actual Benchmark Harvesting / Construction**: `NOT YET STARTED`

