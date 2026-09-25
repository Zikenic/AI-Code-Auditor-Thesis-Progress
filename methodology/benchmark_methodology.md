# Benchmark Dataset & Evaluation Methodology

## 1. Overview & Evaluation Context

The evaluation methodology defines the experimental harness for benchmarking the automated Pull Request auditing system across four core configurations:

- **Configuration A**: Deterministic static analysis alone (Ruff + Semgrep CE).
- **Configuration B**: Heuristic LLM review alone (isolated diff + single-file context).
- **Configuration C**: Hybrid review (Static + LLM) without repository context.
- **Configuration D**: Hybrid review (Static + LLM) augmented with repository-level context retrieval (AST call graphs + pgvector embeddings).

The benchmark dataset is an **evaluation artifact**, not part of the runtime system. It provides an objective, reproducible ground truth to measure detection accuracy and system efficiency.

---

## 2. Dataset Design & Sizing Baseline

| Metric | Target Specification | Design Rationale |
| :--- | :--- | :--- |
| **Total Test Cases** | **Minimum 100 cases (floor baseline)** | Statistically robust baseline for thesis evaluation across 4 configurations. |
| **Defect Balance** | **50% Buggy / 50% Clean** | Avoids artificial inflation of precision or recall; reflects realistic PR intake. |
| **Category Distribution** | **~Balanced across 6 categories** | Category counts kept within 10 cases of each other where practical. |
| **Complexity Mix** | **~50% Single-file / ~50% Cross-file** | Evaluates local reasoning vs. need for repository context retrieval (Config D). |
| **Target Frameworks** | **Python (FastAPI and Flask)** | Modern, widely adopted web backends with active ecosystems. |

---

## 3. The 6 Locked Defect Categories

The benchmark evaluates defect detection across exactly six locked categories:

1. **Category 1: Boundary / Conditional / Logic** (off-by-one, boolean inversions, `None` dereference).
   - *Special Attribute*: Annotated with an orthogonal attribute:
     $$\text{impact} \in \{\text{"functional"}, \text{"security"}\}$$
     This allows distinguishing functional reliability errors from security weaknesses without fracturing the 6-category structure.
2. **Category 2: Input Validation & Sanitization** (missing/flawed schema validation, range checks, output escaping).
3. **Category 3: SQL / ORM Injection** (raw SQL string interpolation, unescaped raw ORM clauses via SQLAlchemy `text()`).
4. **Category 4: Path Traversal / Unsafe File Ops** (directory escape via `../`, arbitrary file write, dangerous file upload).
5. **Category 5: Missing / Broken Authentication** (unprotected sensitive endpoints, unverified JWT signatures).
6. **Category 6: Missing / Broken Authorization** (IDOR/BOLA via user-controlled keys, flawed role logic, vertical escalation).

---

## 4. Development vs. Test Partitioning Protocol

To avoid evaluation bias and prompt overfitting:

- **Split Ratio**: **30% Development Set (30 cases) / 70% Test Set (70 cases)**.
  - *Dev Set*: 15 Buggy / 15 Clean. Used for prompt tuning, static rule filtering, context pruning heuristics, and pipeline debugging.
  - *Test Set*: 35 Buggy / 35 Clean. Strictly locked and held out until final experimental execution.
- **Repository-Family Grouping**: All test cases originating from the same open-source repository are assigned to the same partition (either Dev or Test, never split). This eliminates repository-specific memorization or data leakage.
- **Locking Protocol**: Once curated and verified, the Test Set is frozen. No prompt modifications or parameter adjustments are permitted after unblinding.

---

## 5. Finding Matching & Scoring Rules

To ensure deterministic, automated, and dispute-free evaluation of tool findings against ground truth, the system adapts authoritative matching standards grounded in the **Real-Vuln-Benchmark** methodology ([Real-Vuln-Benchmark GitHub Repository](https://github.com/kolega-ai/Real-Vuln-Benchmark), specifically `scorer/matcher.py`):

1. **Normalized File Path Matching**: The finding's file path must match the ground truth affected file after path normalization (stripping repository prefixes, resolving relative paths).
2. **Category / CWE Matching**: The finding's reported category or CWE must match the case's primary CWE or fall within its pre-declared `alternative_cwe_set`.
3. **Line Proximity Matching**: The reported defect line coordinate must fall within a fixed tolerance window of **$\pm 10$ lines** around the ground-truth pre-fix locus:
   $$\text{Match} \iff \max(\text{start}_{\text{GT}} - 10, 1) \le \text{line}_{\text{Finding}} \le \text{end}_{\text{GT}} + 10$$
4. **One-to-One Ground Truth Consumption**: A single ground-truth defect can be matched by at most one tool finding (avoiding multiple credit for redundant reports).
5. **False Positive Accounting**: Any reported finding that fails to match a ground-truth defect (or any finding reported on a Clean PR) is strictly counted as a **False Positive (FP)**.

---

## 6. Target Evaluation Metrics

The experimental configurations will be benchmarked using standard Information Retrieval and Code Review metrics:

- **Precision ($P$)**: Research target $\ge 75\%$
  $$P = \frac{\text{TP}}{\text{TP} + \text{FP}}$$
- **Recall ($R$)**: Research target $\ge 60\%$
  $$R = \frac{\text{TP}}{\text{TP} + \text{FN}}$$
- **$F_1$-Score**: Research target $\ge 0.67$
  $$F_1 = 2 \cdot \frac{P \cdot R}{P + R}$$
- **False Positive Rate on Clean PRs ($\text{FPR}_{\text{clean}}$)**: Research target $\le 20\%$
  $$\text{FPR} = \frac{\text{FP}_{\text{clean}}}{\text{Total Clean PRs}}$$
- **Auditing Latency**: Operational target $\le 180$ seconds per PR for standard CI workflow feasibility.

---

## 7. Governance: Supervisor-Confirmed vs. Validated Methodology

To maintain rigorous academic governance, methodological elements are clearly demarcated:

- **Supervisor-Confirmed Scope (Foundational)**:
  - Thesis topic: Automated Code Review and Bug Detection for Python Web Backends using Static Analysis & LLM.
  - Core architecture: 4-way comparative evaluation (Configurations A, B, C, D).
  - Target ecosystem: Python web applications (FastAPI & Flask).
  - Delivery format: Pull Request review workflow integrated into GitHub Actions CI/CD.
- **Validated Final Methodology (Technical Specification)**:
  - Locked 6-category defect taxonomy with Category 1 orthogonal impact attribute.
  - Minimum 100 cases baseline floor with 30/70 Dev-Test stratified split.
  - Deterministic $\pm 10$ lines matching tolerance and 1-to-1 ground truth consumption.
  - Multi-CWE representation policy with pre-declared alternative sets and single primary fallback.
  - Performance targets ($P \ge 75\%$, $R \ge 60\%$, Latency $\le 180s$).
