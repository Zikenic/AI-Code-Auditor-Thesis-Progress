# R1 — Ruff vs Semgrep

## Research Status
- **Status**: VERIFIED
- **Research Date**: 2026-09-23
- **Audit & Closure Date**: 2026-09-25
- **Primary Investigator**: Antigravity (Repository Executor)
- **Research Method**: Direct primary documentation extraction, official repository architecture analysis, and CLI output schema auditing (GPT Researcher runner halted due to unconfigured cloud API credentials; direct primary extraction authorized by user).
- **Independent Verification**: Claude (Verified with corrections applied 2026-09-23; citation integrity & CI/CD audit closed 2026-09-25)
- **Verification Result**: VERIFIED (Audited, citation links verified, and closed)
- **Final Authority**: Student (Bui Van Khai) + Supervisor (ThS. Tran Thi Hong Yen)

---

## Research Question
> For an automated Python Pull Request code-auditing system focused on small-to-medium FastAPI/Flask projects, what are the documented capabilities, analysis models, security capabilities, extensibility, CI integration, and practical limitations of Ruff versus Semgrep?

---

## Method
1. **Scope of Investigation**:
   - Primary technical documentation of Ruff (Astral Software Inc.) and Semgrep (Semgrep Inc.).
   - Official source code repositories (`astral-sh/ruff`, `semgrep/semgrep`).
   - Official architecture specifications, tracked issues, and rule registries.
2. **Source Hierarchy Enforced**:
   - **Tier 1 (Authoritative Primary)**: `docs.astral.sh/ruff`, `github.com/astral-sh/ruff`, `semgrep.dev/docs`, `github.com/semgrep/semgrep`, official Semgrep Registry rules, and MITRE CWE specifications.
   - **Tier 2 (Primary Technical)**: Maintainer technical posts and release announcements from Astral and Semgrep Inc.
   - **Tier 3 (Secondary)**: Peer-reviewed benchmarks and public issue trackers.
   - Unverified SEO posts, developer forum commentary, and non-authoritative benchmarks were discarded.
3. **Analytical Constraints**:
   - Factual capabilities are strictly distinguished from engineering suitability judgments.
   - No performance or latency numbers are reported without an explicit, verifiable benchmark workload and hardware/environment context.
   - No winners, scores, or unilateral architecture decisions are declared.

---

## Executive Findings
- **Ruff** is an intra-file linter and code formatter written in Rust, engineered primarily for execution speed and comprehensive static syntax checking. It implements over 900 built-in rules natively, including security smell heuristics derived from `flake8-bandit` (`S` series). It operates via single-pass Abstract Syntax Tree (AST) and token stream inspection on isolated single files. Current documentation notes that third-party plugins are not currently supported (with issue #283 tracking plugin-system work), it does **not** perform data-flow or taint tracking, and its tracked architectural limitation concerns multi-file analysis / resolving semantic information across files (tracked under issue #7447).
- **Semgrep** is a multi-language semantic code search and static application security testing (SAST) engine built on Tree-sitter concrete syntax trees (CST) and an internal AST representation. It is engineered specifically for deep security auditing and pattern matching using developer-friendly YAML rules whose syntax mirrors target source code. In its open-source **Community Edition (CE)**, Semgrep supports intra-file data-flow and taint analysis (`mode: taint`) tracking untrusted input from sources to sinks through sanitizers and propagators, including cross-function taint within a single file. Its findings carry native structured metadata including explicit CWE IDs and OWASP categories. However, cross-file / inter-file taint analysis across multiple files is proprietary and restricted to the commercial **Semgrep Pro Engine**.
- **Complementarity**: Ruff provides low-overhead, rapid syntactic linting and style/smell detection suitable for immediate developer feedback and basic code hygiene. Semgrep Community Edition provides expressive, security-centric semantic pattern matching and taint tracking capable of identifying complex injection and validation flaws within a single file. Neither tool in its open-source form provides repository-wide, cross-file semantic reasoning, leaving cross-file context gaps that must be addressed at higher pipeline layers (e.g., repository graph extraction and LLM semantic auditing).

---

## Ruff

### Capabilities
- **Core Technology & Engine**: Written in Rust by Astral Software Inc. Uses a custom Rust-based Python parser (`ruff_python_ast`) and lexer.
- **Analysis Model**: Single-pass, intra-file AST visitor and token stream inspection. Checks code strictly one file at a time without loading surrounding modules.
- **Rule Parity**: Implements native Rust re-implementations of popular Python linters and plugins (over 900 built-in rules): Pyflakes (`F`), pycodestyle (`E`, `W`), isort (`I`), pydocstyle (`D`), pyupgrade (`UP`), pep8-naming (`N`), flake8-bugbear (`B`), flake8-comprehensions (`C4`), flake8-simplify (`SIM`), and flake8-bandit (`S`).
- **Auto-Fix Support**: Provides automated code transformation for select rules via `ruff check --fix` (safe fixes) and `ruff check --fix --unsafe-fixes` (potentially semantic-altering fixes).

### Security
- **Rule Set**: Integrates rules ported from `flake8-bandit` under the `S` prefix (`S101` through `S703`).
- **Detectable Vulnerabilities**:
  - Hardcoded credentials, passwords, and tokens (`S105`, `S106`, `S107`).
  - Hardcoded SQL query formatting/concatenation (`S608`).
  - Insecure process execution with shell invocation (`S602`, `S605`).
  - Cryptographically weak algorithms and random generators (`S303`, `S304`, `S305`, `S311`).
  - Insecure XML parsing susceptible to entity expansion (`S313`–`S320`).
- **Security Depth**: Syntactic pattern matching only. Ruff does not construct a Control Flow Graph (CFG) or perform data-flow/taint analysis. For example, `S608` flags string formatting inside SQL-like strings, but Ruff cannot determine whether the formatted variable originated from untrusted user input or an internal constant.

### CI / Automation
- **Execution & Ingestion**: CLI `ruff check [files/dirs]`. Official GitHub Action available (`astral-sh/ruff-action`).
- **Machine-Readable Formats**: Supports `json`, `json-lines`, `sarif`, `junit`, `github` (inline annotations), `gitlab`, `pylint`, `rdjson`, and `azure`.
- **Finding Schema (JSON)**: Emits `code`, `message`, `filename`, `location` (`row`, `column`), `end_location`, `fix`, `url`, and `noqa_row`.
- **CWE / OWASP Attributes**: Ruff does **not** emit structured CWE or OWASP identifiers in its JSON findings. CWE identifiers are cited only informally within the online rule documentation.

### Extensibility
- **Custom Rules / Plugins**: Current Ruff documentation states that third-party plugins are not currently supported. Astral GitHub Issue #283 tracks plugin-system design and community requests. Custom rules cannot currently be added via external DSL without modifying and recompiling the Ruff Rust source tree.
- **Rule Authoring**: Adding a new rule requires writing Rust code against `ruff_python_ast` and compiling a custom fork of the Ruff binary.

### Limitations
- **Multi-File Analysis Limitation**: Ruff's tracked architectural limitation concerns multi-file analysis and resolving semantic information across files (tracked under Astral GitHub Issue #7447). Astral is developing a separate type-checking engine named "Red-Knot" to address whole-program type analysis, but multi-file resolution is not part of Ruff's current production linter.
- **No Taint / Data-Flow Tracking**: Cannot trace variable origins, sanitization functions, or cross-function argument flows.
- **High False Positive / False Negative Ratio in Deep Logic**: Syntactic rules cannot distinguish between safe internal constants and malicious user-supplied strings in complex expressions.

---

## Semgrep

### Capabilities
- **Core Technology & Engine**: Developed by Semgrep Inc. Built on Tree-sitter parsers (concrete syntax trees) and an internal AST representation written in OCaml and Python.
- **Analysis Model**: Concrete syntax pattern matching. Patterns are written in the target language syntax (Python) augmented with metavariables (`$VAR`, `$X`) and ellipsis operators (`...`).
- **Semantic Equivalences**: Abstracted pattern matching that ignores whitespace, comments, and variable alias variations within the analyzed scope (e.g., `import os as my_os` followed by `my_os.system($X)` matches a pattern targeting `os.system(...)`).

### Security
- **Taint Analysis (Community Edition — `mode: taint`)**:
  - Supports intra-file data-flow tracking from designated entry points (`pattern-sources`) to vulnerable execution points (`pattern-sinks`).
  - Within a single file, Semgrep Community Edition can track taint across functions (intra-file inter-procedural data-flow).
  - Allows specifying intermediate transformations (`pattern-propagators`) and neutralizing functions (`pattern-sanitizers`).
  - Supports side-effect taint tracking and sanitization verification within a function/file.
- **Ecosystem & Registries**:
  - Semgrep Registry contains hundreds of curated security rules covering OWASP Top 10, CWE Top 25, and major Python frameworks including FastAPI, Flask, Django, and SQLAlchemy.
- **Metadata Standards**:
  - Every security rule includes standardized top-level `metadata` fields: `cwe` (e.g., `"CWE-89: SQL Injection"`), `owasp` (e.g., `"A03:2021 - Injection"`), `confidence`, `likelihood`, `impact`, and external CVE/research references.

### CI / Automation
- **Execution & Ingestion**: CLI `semgrep scan`, `semgrep ci`. Official GitHub Action available (`semgrep/semgrep-action`).
- **Machine-Readable Formats**: Native support for `--json`, `--sarif`, and `--junit-xml`.
- **Finding Schema (JSON)**: Findings contain `check_id`, `path`, `start` (`line`, `col`), `end` (`line`, `col`), `extra` (`message`, `severity`, `lines`), and full rule metadata under `extra.metadata` (including `cwe`, `owasp`, `references`).
- **Auto-Fix**: Supported via the `fix:` directive inside rule definitions, allowing regex or template-based string replacements upon finding match.

### Extensibility
- **Rule Authoring**: First-class, developer-friendly YAML rule syntax. Custom rules can be written, tested, and executed immediately using `semgrep --config <my-rule.yml> .` without compilation.
- **Testing Framework**: Native rule test suite support using comment-based assertions (`# ruleid: rule-id` / `# ok: rule-id`).

### Limitations
- **Single-File Scope in Community Edition (OSS)**: The open-source Semgrep Community Edition (CE) performs only intra-file analysis. It cannot track taint, symbols, or function calls across multiple files.
- **Proprietary Cross-File Engine**: Deep cross-file / inter-file taint analysis across multiple files requires the proprietary Semgrep Pro Engine (Semgrep Code, commercial license).
- **Execution Performance**: Semgrep's pattern matching and data-flow analysis can involve more computational work than Ruff's linting architecture, but no authoritative head-to-head Ruff-vs-Semgrep benchmark was identified in this research. Therefore no numerical performance ratio is claimed. Complex nested patterns (`<... $X ...>`) can cause significant evaluation latency or memory timeouts in large codebases if unoptimized.

---

## GitHub Actions CI/CD Integration for Pull Request Auditing

To operate as an automated Pull Request code auditor, static and semantic analysis tools must integrate reliably into GitHub Actions workflows. The authoritative integration mechanics are documented as follows:

### 1. Workflow Triggers & Event Context
- **Trigger Event**: The `pull_request` workflow event fires on PR activity (by default: `opened`, `synchronize` [new commits pushed], and `reopened`).
- **Target Git References**:
  - `github.event.pull_request.head.sha`: The commit SHA of the incoming feature branch tip.
  - `github.event.pull_request.base.sha`: The commit SHA of the target branch (e.g., `main`).
  - Merge ref: GitHub also generates an ephemeral merge commit at `refs/pull/<pr_number>/merge` representing the simulated result of merging `head` into `base`.

### 2. Repository Checkout Configuration
- **Checkout Action**: `actions/checkout@v4`.
- **Fetch Depth Requirement**: By default, `actions/checkout` performs a shallow clone with `fetch-depth: 1` checking out only the merge commit. For diff-aware auditing (identifying changed files, computing commit range `base...head`, or running incremental linters), the runner requires either:
  - `fetch-depth: 0` (full history clone, enabling arbitrary `git diff origin/main...HEAD` comparisons).
  - Explicit fetch of the base and head branches (`git fetch origin main ${{ github.event.pull_request.head.ref }}`).

### 3. Deterministic Tool Execution in CI Runners
- **Runner Environment**: Standard GitHub-hosted runners (`ubuntu-latest`) support user-space execution of Ruff and Semgrep via `uv run ruff ...` or containerized actions.
- **CLI Commands**:
  - Ruff: `ruff check --output-format json --output-file ruff-findings.json .`
  - Semgrep: `semgrep scan --config auto --json --output semgrep-findings.json .`
- **Exit Code Management**: Static linters and security scanners exit with non-zero status codes (e.g., `1`) when rule violations are found. In an auditing pipeline where deterministic findings are ingested by downstream stages (e.g., Repo RAG or LLM review), tool steps must prevent premature job termination by capturing exit codes or using `continue-on-error: true` (or `--exit-zero` where supported).

### 4. Passing Findings to Subsequent Pipeline Stages
- **Intra-Job Pipeline**: Steps in the same job access structured outputs written to `$RUNNER_TEMP/` or workspace files (`ruff-findings.json`, `semgrep-findings.json`).
- **Inter-Job Pipeline**: Separate workflow jobs communicate across runner boundaries by uploading finding files via `actions/upload-artifact@v4` and downloading them in downstream jobs via `actions/download-artifact@v4`.
- **Step Outputs**: Short summary metadata (e.g., finding count, detected categories) can be passed between steps via `$GITHUB_OUTPUT` environment files (`echo "finding_count=$COUNT" >> "$GITHUB_OUTPUT"`).

### 5. Publishing Findings Back to GitHub
- **PR Inline Review Comments**: Findings associated with specific diff hunks can be posted directly as line-level review comments using the GitHub REST API (`POST /repos/{owner}/{repo}/pulls/{pull_number}/comments`) or GraphQL API via `actions/github-script@v7`. Comments on lines outside the PR diff cannot be posted as inline review comments and must be posted as general PR issue comments (`POST /repos/{owner}/{repo}/issues/{pull_number}/comments`).
- **GitHub Workflow Annotations**: Tools can emit workflow commands directly to stdout (`::warning file={name},line={line},title={title}::{message}` or `::error ...`), which GitHub automatically parses into inline annotations on the PR "Files changed" tab and the workflow run summary.
- **GitHub Code Scanning (SARIF)**: Both Ruff and Semgrep support emitting findings in OASIS SARIF format (`ruff check --output-format sarif`, `semgrep scan --sarif`). These SARIF files can be uploaded directly to GitHub Advanced Security / Code Scanning via `github/codeql-action/upload-sarif@v3`, integrating findings into the repository's native "Security" tab.

---

## Comparative Evidence

| Dimension | Ruff | Semgrep (OSS Community Edition) |
| :--- | :--- | :--- |
| **Primary purpose** | Ultra-fast Python code linting, formatting, and syntactic code hygiene | Semantic code search, custom standards enforcement, and SAST vulnerability detection |
| **Analysis approach** | Single-pass AST visitor and token stream inspection (Rust) | Tree-sitter CST / AST pattern matching with metavariables and taint tracking |
| **Python support** | First-class, highly optimized Python parser (`ruff_python_ast`) | First-class, mature Python Tree-sitter grammar |
| **AST / structural analysis** | Direct AST node visitation; checks exact node types and attributes | Concrete code pattern syntax matching AST structures across variable renames and formatting |
| **Security rules** | Re-implements `flake8-bandit` rules (`S` series); detects syntactic patterns | Extensive Semgrep Registry security rules targeting OWASP, CWE, and Python web frameworks |
| **Custom rules** | Not supported. No user DSL or runtime plugin system (GitHub #283) | Fully supported via declarative YAML rule definitions without compilation |
| **CWE metadata/mapping** | No structured CWE field in finding outputs; cited only in doc pages | First-class structured `metadata.cwe` field emitted in JSON and SARIF payloads |
| **OWASP-related coverage** | Informal; individual bandit rules touch OWASP topics without metadata tags | First-class structured `metadata.owasp` field categorized by OWASP Top 10 standards |
| **Data-flow / taint analysis** | None. Purely syntactic inspection | Supported intra-file via `mode: taint` (`pattern-sources`, `sinks`, `sanitizers`) |
| **Cross-file / repository analysis** | None. Strictly single-file (multi-file deferred to separate Red-Knot project) | None in OSS CE (intra-file only). Cross-file requires commercial Semgrep Pro Engine |
| **CI integration** | CLI exit codes, `astral-sh/ruff-action`, pre-commit | CLI exit codes, `semgrep ci`, `semgrep/semgrep-action`, pre-commit |
| **Machine-readable findings** | `json`, `json-lines`, `sarif`, `junit`, `github`, `gitlab` | `json`, `sarif`, `junit-xml` |
| **Auto-fix capability** | Native `--fix` and `--unsafe-fixes` across hundreds of standard rules | Template-based `fix:` directive defined per rule |
| **Configuration** | `pyproject.toml` (`[tool.ruff]`), `ruff.toml` | YAML config files (`semgrep.yml`), remote registry packs (`p/python`, `p/owasp-top-ten`) |
| **Documented performance characteristics** | 10-100x faster than Python linters (Flake8); fine-grained `.ruff_cache` | Semgrep's pattern matching and data-flow analysis involve more computational work than linting; no authoritative head-to-head benchmark identified (supports `--jobs`, `--time`, `.semgrepignore`) |
| **Important limitations for this thesis** | Cannot track user-taint; no custom rules; no structured CWE output | OSS is limited to single-file taint; cross-file calls invisible without proprietary engine |

---

## Claims Requiring Careful Interpretation

```text
Claim: "Ruff performs AST analysis."
Source: Astral Official Documentation — Ruff Architecture
Publisher: Astral Software Inc.
URL: https://docs.astral.sh/ruff/
Publication/update date: 2026
Access date: 2026-09-23
What the source actually establishes: Ruff builds and traverses a single-file AST using `ruff_python_ast` in Rust. It does NOT establish that Ruff performs abstract interpretation, control-flow graphing, data-flow analysis, or cross-file symbol resolution.
Confidence: HIGH
```

```text
Claim: "Semgrep supports taint analysis."
Source: Semgrep Official Documentation — Taint Analysis
Publisher: Semgrep Inc.
URL: https://docs.semgrep.dev/writing-rules/data-flow/taint-mode/overview
Publication/update date: 2026
Access date: 2026-09-23
What the source actually establishes: Semgrep supports source-to-sink intra-file taint analysis via `mode: taint` with propagators and sanitizers in its open-source CLI. It does NOT establish that the open-source CLI performs cross-file or whole-repository taint tracking.
Confidence: HIGH
```

```text
Claim: "Ruff has security-oriented rules."
Source: Astral Official Documentation — Ruff Rules (Flake8-bandit)
Publisher: Astral Software Inc.
URL: https://docs.astral.sh/ruff/rules/#flake8-bandit-s
Publication/update date: 2026
Access date: 2026-09-23
What the source actually establishes: Ruff implements rules ported from `flake8-bandit` (`S` prefix) that identify syntactic vulnerability patterns (e.g., hardcoded passwords, shell=True, string SQL concatenation). It does NOT establish that Ruff validates whether an input actually originates from untrusted user data.
Confidence: HIGH
```

```text
Claim: "Semgrep supports cross-file / inter-file analysis."
Source: Semgrep Official Documentation — Cross-File (Inter-File) Analysis
Publisher: Semgrep Inc.
URL: https://docs.semgrep.dev/semgrep-code/semgrep-pro-engine-intro
Publication/update date: 2026
Access date: 2026-09-23
What the source actually establishes: Cross-file analysis is a feature of the proprietary, closed-source Semgrep Pro Engine (commercial product). It is NOT present in the open-source Community Edition (CE) engine.
Confidence: HIGH
```

```text
Claim: "Ruff is 10-100x faster than Flake8."
Source: Astral Official Documentation — Ruff Overview & Benchmark
Publisher: Astral Software Inc.
URL: https://docs.astral.sh/ruff/
Publication/update date: 2026
Access date: 2026-09-23
What the source actually establishes: Measured on CPython linting benchmarks comparing single-threaded Python linters (Flake8) against multi-threaded native Rust implementation. It does NOT establish a direct speed comparison against Semgrep executing taint analysis rules, which solve a different computational problem.
Confidence: HIGH
```

```text
Claim: "Ruff does not support user-defined custom plugins or rules."
Source: Astral GitHub Issue Tracker — Issue #283 ("Plugin system / custom rules")
Publisher: Astral Software Inc.
URL: https://github.com/astral-sh/ruff/issues/283
Publication/update date: 2026
Access date: 2026-09-23
What the source actually establishes: A runtime plugin system or custom rule DSL is not available in Ruff. Custom rules currently require writing Rust code inside the compiler tree.
Confidence: HIGH
```

```text
Claim: "Ruff linter does not perform cross-file analysis."
Source: Astral GitHub Issue Tracker — Issue #7447 ("Multi-file analysis")
Publisher: Astral Software Inc.
URL: https://github.com/astral-sh/ruff/issues/7447
Publication/update date: 2026
Access date: 2026-09-23
What the source actually establishes: Ruff's linter architecture is strictly single-file. Whole-program analysis is assigned to the separate "Red-Knot" project currently under development.
Confidence: HIGH
```

---

## Source Register

1. **Ruff Official Documentation**
   - *Publisher*: Astral Software Inc.
   - *URL*: `https://docs.astral.sh/ruff/`
   - *Topics*: Architecture, linter rules, Flake8 parity, performance benchmarks, configuration.
   - *Tier*: 1 (Authoritative Primary)

2. **Ruff Rules Reference — Security (`flake8-bandit`)**
   - *Publisher*: Astral Software Inc.
   - *URL*: `https://docs.astral.sh/ruff/rules/#flake8-bandit-s`
   - *Topics*: `S101`–`S703` rule definitions, hardcoded secrets, shell injections, cryptographic weaknesses, CWE documentation cross-references.
   - *Tier*: 1 (Authoritative Primary)

3. **Ruff Output Serialization Documentation**
   - *Publisher*: Astral Software Inc.
   - *URL*: `https://docs.astral.sh/ruff/settings/#output-format`
   - *Topics*: Supported serialization formats (`json`, `sarif`, `github`, etc.) and finding schema.
   - *Tier*: 1 (Authoritative Primary)

4. **Astral GitHub Repository — Issue #283**
   - *Publisher*: Astral Software Inc.
   - *URL*: `https://github.com/astral-sh/ruff/issues/283`
   - *Topics*: Status of plugin API and custom user rules in Ruff.
   - *Tier*: 1 (Authoritative Primary Repository)

5. **Astral GitHub Repository — Issue #7447**
   - *Publisher*: Astral Software Inc.
   - *URL*: `https://github.com/astral-sh/ruff/issues/7447`
   - *Topics*: Multi-file analysis architectural boundaries and separation from Red-Knot.
   - *Tier*: 1 (Authoritative Primary Repository)

6. **Semgrep Official Documentation — Taint Analysis**
   - *Publisher*: Semgrep Inc.
   - *URL*: `https://docs.semgrep.dev/writing-rules/data-flow/taint-mode/overview`
   - *Topics*: `mode: taint`, sources, sinks, sanitizers, propagators, dataflow tracking.
   - *Tier*: 1 (Authoritative Primary)

7. **Semgrep Official Documentation — Rule Syntax & Metadata**
   - *Publisher*: Semgrep Inc.
   - *URL*: `https://docs.semgrep.dev/writing-rules/rule-syntax`
   - *Topics*: YAML rule format, metavariables, ellipsis, `metadata.cwe`, `metadata.owasp`.
   - *Tier*: 1 (Authoritative Primary)

8. **Semgrep Official Documentation — Cross-File (Inter-File) Analysis**
   - *Publisher*: Semgrep Inc.
   - *URL*: `https://docs.semgrep.dev/semgrep-code/semgrep-pro-engine-intro` (and `https://docs.semgrep.dev/semgrep-pro-vs-oss`)
   - *Topics*: Pro Engine cross-file taint capabilities versus Community Edition single-file boundaries.
   - *Tier*: 1 (Authoritative Primary)

9. **Semgrep Official Documentation — CI & CLI Configuration**
   - *Publisher*: Semgrep Inc.
   - *URL*: `https://docs.semgrep.dev/semgrep-ci/sample-ci-configs` (and `https://docs.semgrep.dev/for-developers/cli`)
   - *Topics*: CI execution (`semgrep scan`), SARIF output, diff-aware scanning, multiprocessing.
   - *Tier*: 1 (Authoritative Primary)

10. **GitHub Actions Official Documentation**
    - *Publisher*: GitHub Inc.
    - *URL*: `https://docs.github.com/en/actions`
    - *Topics*: `pull_request` event triggers, `actions/checkout` clone depth, workflow artifacts, workflow commands/annotations, and SARIF upload to Code Scanning.
    - *Tier*: 1 (Authoritative Primary)

---

## Unverified / Uncertain Claims
- **Exact Semgrep CE vs Ruff Execution Time Ratio on Identical Repositories**: While Ruff publishes benchmarks against Flake8 (CPython codebase), neither Astral nor Semgrep Inc. publishes an authoritative head-to-head benchmark against each other because their rule sets and analysis engines address fundamentally different inspection tasks. Any claim stating an exact multiplier (e.g., "Ruff is 50x faster than Semgrep") is unverified and context-dependent.
- **Red-Knot Release Timeline**: The release date and exact feature set of Astral's multi-file "Red-Knot" engine for Python remain active development items and should not be assumed as available for this thesis window (Sep–Dec 2026).

---

## Researcher Notes
- **Implications for AI Code Auditor Deterministic Layer**:
  1. **Two-Tier Deterministic Strategy**: Ruff and Semgrep are non-redundant and serve complementary functions:
     - Ruff acts as a first-line, near-instantaneous filter for syntactic hygiene, basic bug smells (`flake8-bugbear`), and known anti-patterns (`flake8-bandit`).
     - Semgrep acts as the deep semantic security rule checker, tracking intra-file taint from API parameters to query/eval sinks and providing structured CWE metadata.
  2. **The Cross-File Blindspot**: Because both open-source tools (Ruff and Semgrep CE) operate strictly on a **single-file** basis, neither can detect bugs or security vulnerabilities that span multiple files (e.g., an unvalidated parameter in `routes.py` passed to an unsanitized helper function in `services.py` that executes a database query in `models.py`).
  3. **Role of Repo RAG & LLM Semantic Review**: This empirical finding validates the core hypothesis of the thesis manifesto: the deterministic static analysis layer cannot resolve cross-file dependencies on its own; a repository-level context retrieval mechanism (AST import/call graphs + vector search) coupled with an LLM semantic layer is required to bridge the cross-file audit gap.
