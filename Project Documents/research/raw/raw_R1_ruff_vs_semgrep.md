# Raw Research Capture: R1 — Ruff vs Semgrep

## 1. Execution Log & Toolchain Record
- **Task**: Research Package R1 — Ruff vs Semgrep capabilities, analysis models, security, CI, and practical limitations for small-to-medium FastAPI/Flask Python projects.
- **Date**: 2026-09-23
- **Primary Tool**: GPT Researcher execution environment (`.agent-tools/gpt-researcher/.venv/`).
- **Invocation**: `.agent-tools\gpt-researcher\.venv\Scripts\python.exe .agent-tools\gpt-researcher\run_research.py --query "Ruff vs Semgrep static analysis" --output "Project Documents/research/raw/raw_R1_ruff_vs_semgrep.md"`
- **Execution Limitation / Fallback**:
  - `run_research.py` was invoked and initialized `GPTResearcher`.
  - The runtime halted with `openai.OpenAIError: Missing credentials. Please pass an api_key...` because no external LLM API key (OpenAI/Gemini/Anthropic/Groq) was present in `.agent-tools/gpt-researcher/.env` or environment variables.
  - Per interactive user consultation, research proceeded via direct primary documentation extraction, official repository issue audits, and syntax analysis using Antigravity's research toolchain.

---

## 2. Raw Technical Evidence Collected

### Category A: Ruff (Astral)
- **Primary Definition**: Ruff is an extremely fast Python linter and code formatter written in Rust (Astral Software Inc.).
- **Parser & Analysis Architecture**:
  - Employs a custom Rust-based Python parser (`ruff_python_ast`) and lexer.
  - Traversal model: Single-pass AST visitor and token stream inspection on single files.
  - Multi-file status: Ruff's linter operates on a strictly single-file basis (GitHub Issue astral-sh/ruff#7447). Cross-file symbol resolution and type-checking are explicitly separated into Astral's experimental "Red-Knot" project, which is not integrated into stable Ruff linting.
- **Rule Coverage**:
  - Implements >800 rules natively in Rust, providing drop-in parity for Flake8, pycodestyle (`E`, `W`), Pyflakes (`F`), isort (`I`), pydocstyle (`D`), pyupgrade (`UP`), pep8-naming (`N`), flake8-bugbear (`B`), flake8-comprehensions (`C4`), and flake8-bandit (`S`).
- **Security Capabilities**:
  - Integrates `flake8-bandit` rules (`S` series: S101 through S703).
  - Common patterns caught:
    - S105, S106, S107: Hardcoded passwords, tokens, and default credentials.
    - S608: Hardcoded SQL injection via string formatting or concatenation.
    - S602, S605: Starting a process with a shell / untrusted subprocess execution.
    - S303, S304, S305: Insecure cryptographic algorithms (MD5, SHA1, DES).
    - S311: Insecure pseudo-random number generators (`random` module).
    - S313-S320: XML entity injection vulnerabilities (`xml.etree`, `minidom`, `pulldom`).
  - Analysis depth: Pure AST pattern heuristics. Ruff does NOT perform dataflow or taint tracking. It flags the syntax of the call or variable assignment regardless of whether the input is user-tainted.
- **Rule Extensibility / Plugins**:
  - Ruff does NOT support third-party plugins or user-defined custom rules (GitHub Issue astral-sh/ruff#283). All rules must be written in Rust and compiled directly into the binary.
- **CI / Machine-Readable Automation**:
  - Command: `ruff check [path]`
  - Output formats: `full` (default), `concise`, `grouped`, `json`, `json-lines`, `junit`, `github`, `gitlab`, `pylint`, `rdjson`, `azure`, `sarif`.
  - JSON output schema: Fields include `cell`, `code`, `filename`, `location` (`row`, `column`), `end_location`, `message`, `fix`, `noqa_row`, `url`. No native structured `cwe` or `owasp` metadata keys are emitted in the JSON payload (CWEs are cited only in documentation markdown).
  - Auto-fix: Supports `ruff check --fix` and `ruff check --fix --unsafe-fixes`.
- **Performance Characteristics**:
  - 10-100x faster than legacy Flake8/Black pipelines. Written in Rust with fine-grained per-file content-hashed caching stored in `.ruff_cache`.

### Category B: Semgrep (Semgrep Inc.)
- **Primary Definition**: Semgrep is a fast, open-source static analysis engine for searching code, enforcing coding standards, and discovering security vulnerabilities using pattern matching that resembles source code.
- **Parser & Analysis Architecture**:
  - Built on Tree-sitter concrete syntax trees (CST) and an internal AST representation.
  - Pattern syntax: Uses concrete code syntax with metavariables (`$X`, `$USER_INPUT`) and ellipsis operators (`...`) to match arbitrary statements, expressions, or arguments.
  - Matches across formatting variations, whitespace, and variable aliases within a function/file.
- **Taint & Data-Flow Analysis**:
  - First-class taint mode enabled via `mode: taint` in rule definitions.
  - Syntax components:
    - `pattern-sources`: Where untrusted input enters (e.g. `request.args.get(...)`, `request.json(...)`).
    - `pattern-sinks`: Where untrusted input causes harm (e.g. `db.execute(...)`, `eval(...)`, `open(...)`).
    - `pattern-propagators`: Explicit propagation paths between variables or through functions.
    - `pattern-sanitizers`: Functions or sanitization patterns that neutralize the taint (e.g. `shlex.quote(...)`, `int(...)`).
- **Security Capabilities & Metadata**:
  - Semgrep Registry features extensive curated security rules targeting OWASP Top 10, CWE Top 25, and Python web frameworks (FastAPI, Flask, Django, SQLAlchemy).
  - Standardized rule `metadata`:
    - `cwe`: Explicit CWE strings (e.g. `"CWE-89: Improper Neutralization of Special Elements used in an SQL Injection"`).
    - `owasp`: OWASP category strings (e.g. `"A03:2021 - Injection"`).
    - `confidence`, `likelihood`, `impact`, `subcategory`.
  - All metadata is emitted directly in machine-readable JSON (`extra.metadata.cwe`) and SARIF outputs.
- **Rule Extensibility**:
  - High extensibility. Rules are defined in pure YAML. Developers can create, test, and maintain project-specific rules without compiling code.
- **Cross-File / Inter-File Boundary**:
  - Open-Source Semgrep Community Edition (CE) is strictly intra-file / intra-procedural.
  - Cross-file / inter-file dataflow analysis is exclusive to the proprietary, closed-source Semgrep Pro Engine (Semgrep Code, commercial license).
- **CI / Machine-Readable Automation**:
  - CLI: `semgrep scan`, `semgrep ci`.
  - Machine-readable outputs: `--json`, `--sarif`, `--junit-xml`.
  - Auto-fix: Supported via the `fix:` key in rule definitions.
- **Performance Characteristics**:
  - Written in OCaml/Python. Slower than native Rust linters like Ruff by 1 to 2 orders of magnitude on large codebases, but significantly deeper due to pattern evaluation and dataflow tracking. Supports `--jobs`, `.semgrepignore`, `--time`, and `--max-memory`.
