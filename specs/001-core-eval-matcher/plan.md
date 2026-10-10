# Implementation Plan: Core Domain Contracts, Configuration Dispatch, and Offline Evaluation Matcher

**Feature ID**: `001-core-eval-matcher`  
**Phase**: `Implementation Architecture & Execution Plan`  

---

## 1. Architecture & Package Layout

We establish the Python package `auditor` under `src/` as a modular Python package adhering to Python packaging standards (`pyproject.toml`):

```text
src/
└── auditor/
    ├── __init__.py
    ├── models/
    │   ├── __init__.py
    │   ├── config.py         # AuditConfiguration (A, B, C, D)
    │   ├── request.py        # AuditRequest
    │   ├── finding.py        # PredictedFinding, DetectionLayer
    │   ├── ground_truth.py   # GroundTruthDefect, BenchmarkCase, ImpactType
    │   ├── result.py         # AuditRunResult, EvaluationMetrics
    │   └── taxonomy.py       # TaxonomyConfig, active approved taxonomy validator
    ├── matcher/
    │   ├── __init__.py
    │   ├── path_utils.py     # Path normalization & safe prefix removal
    │   ├── location.py       # Range-based locus overlap & ±10 lines tolerance logic
    │   ├── bipartite.py      # Maximum-cardinality bipartite matching (Hopcroft-Karp / DFS)
    │   └── engine.py         # OfflineEvaluationMatcher & score calculation
    └── orchestration/
        ├── __init__.py
        ├── interfaces.py     # IStaticAnalysisEngine, ILlmReviewEngine, IRepoContextRetriever
        └── dispatcher.py     # ConfigurationDispatcher enforcing A, B, C, D boundaries
tests/
├── __init__.py
├── test_models.py            # Taxonomy, impact, CWE, and Pydantic validation tests
├── test_path_utils.py        # POSIX/Windows normalization & prefix tests
├── test_matcher.py           # Evaluation matching rules, ±10/±11 boundary, multi-line, 1-to-1
└── test_dispatcher.py        # Configuration dispatch isolation & stage contracts
```

---

## 2. Implementation Phases

### Phase 1: Environment & Packaging Baseline
- Create `pyproject.toml` defining the project metadata, dependencies (`pydantic>=2.0.0`), and test runner configuration (`pytest`).
- Establish `src/auditor/` and `tests/` directories.

### Phase 2: Domain Contracts & Taxonomy Engine
- Implement `auditor.models.config`: `AuditConfiguration` (`A`, `B`, `C`, `D`).
- Implement `auditor.models.taxonomy`: `TaxonomyConfig` with default active categories `{1, 2, 3, 4, 5, 6}`, absolute max ceiling `8`, and dynamic category validator.
- Implement `auditor.models.finding`: `PredictedFinding` with line ranges, layer tag, CWEs.
- Implement `auditor.models.ground_truth`: `GroundTruthDefect` with mandatory `impact = functional | security` on Category 1, pre-declared alternative CWEs.
- Implement `auditor.models.result`: `AuditRunResult`, `EvaluationMetrics`.

### Phase 3: Offline Evaluation Matcher
- Implement `auditor.matcher.path_utils`: Normalized file path comparison across platforms.
- Implement `auditor.matcher.location`:
  - Range overlap: $\max(s_1, s_2) \le \min(e_1, e_2)$.
  - Tolerance window: $[\max(s_{\text{GT}} - 10, 1), e_{\text{GT}} + 10]$ intersection.
  - Coordinate validity check (rejecting missing, 0, or negative lines).
- Implement `auditor.matcher.bipartite`:
  - Construct bipartite graph between valid candidate pairs (Prediction $i$, GT $j$).
  - Solve maximum-cardinality matching deterministically using augmenting paths with deterministic tie-breaking.
- Implement `auditor.matcher.engine`:
  - Full evaluation runner: classifies TPs, FPs (unmatched on buggy PRs + all on clean PRs), FNs (unmatched GT).
  - Calculates Precision, Recall, F1 with safe zero-division handling.

### Phase 4: Core Orchestration Contracts & Dispatcher
- Implement `auditor.orchestration.interfaces`: Abstract base classes for static, LLM, and context components.
- Implement `auditor.orchestration.dispatcher`:
  - Implements `dispatch(request: AuditRequest, ...) -> AuditRunResult`.
  - Config A: static analysis only.
  - Config B: LLM review with diff only.
  - Config C: static analysis + LLM review with static summary.
  - Config D: hybrid analysis with static analysis, repo context, and LLM review.
- Pure framework-neutral Python logic without web server dependencies.

### Phase 5: Verification & Quality Gates
- Execute test suite: `python -m pytest -v`.
- Execute static analysis & formatting checks: `python -m ruff check src tests` and `python -m ruff format --check src tests`.
