# Tasks: Core Domain Contracts, Configuration Dispatch, and Offline Evaluation Matcher

**Feature ID**: `001-core-eval-matcher`  
**Status**: `Completed`  

---

## Task Breakdown

### Phase 1: Setup & Packaging Baseline
- [x] **T1.1**: Initialize local Git repository with strict `.gitignore` (exclude `.agent-tools/`, `scratch/`, secrets, caches).
- [x] **T1.2**: Populate `.specify/memory/constitution.md` with 9 enforceable thesis principles.
- [x] **T1.3**: Author Feature 1 Spec Kit deliverables (`spec.md`, `plan.md`, `tasks.md`).
- [x] **T1.4**: Create `pyproject.toml` with project metadata, dependencies (`pydantic>=2.0.0`), and `pytest` / `ruff` configurations.
- [x] **T1.5**: Create directory structure under `src/auditor/` and `tests/`.

### Phase 2: Domain Models & Taxonomy Engine
- [x] **T2.1**: Implement `AuditConfiguration` enum (`A`, `B`, `C`, `D`) in `src/auditor/models/config.py`.
- [x] **T2.2**: Implement `TaxonomyConfig` and active taxonomy validator in `src/auditor/models/taxonomy.py` (default 1..6, max cap 8, governed expansion).
- [x] **T2.3**: Implement `PredictedFinding` and `DetectionLayer` in `src/auditor/models/finding.py`.
- [x] **T2.4**: Implement `GroundTruthDefect` (with required Category 1 `impact`), `BenchmarkCase` in `src/auditor/models/ground_truth.py`.
- [x] **T2.5**: Implement `AuditRequest`, `AuditRunResult`, and `EvaluationMetrics` in `src/auditor/models/request.py` and `result.py`.

### Phase 3: Offline Evaluation Matcher
- [x] **T3.1**: Implement normalized path matching and prefix stripping in `src/auditor/matcher/path_utils.py`.
- [x] **T3.2**: Implement range-based location predicate, overlap math, and $\pm 10$ lines tolerance in `src/auditor/matcher/location.py`.
- [x] **T3.3**: Implement deterministic maximum-cardinality bipartite matching in `src/auditor/matcher/bipartite.py`.
- [x] **T3.4**: Implement `OfflineEvaluationMatcher` scoring engine in `src/auditor/matcher/engine.py` (TP, FP on buggy/clean PRs, FN, Precision, Recall, F1).

### Phase 4: Core Orchestration Contracts & Dispatcher
- [x] **T4.1**: Implement abstract interfaces (`IStaticAnalysisEngine`, `ILlmReviewEngine`, `IRepoContextRetriever`) in `src/auditor/orchestration/interfaces.py`.
- [x] **T4.2**: Implement framework-agnostic `ConfigurationDispatcher` enforcing Configuration A–D execution boundaries in `src/auditor/orchestration/dispatcher.py`.

### Phase 5: Verification, Quality Gates & Documentation
- [x] **T5.1**: Implement unit tests in `tests/test_models.py` (taxonomy bounds, Category 1 impact, CWE sets).
- [x] **T5.2**: Implement unit tests in `tests/test_path_utils.py` (Windows vs POSIX paths, prefix stripping).
- [x] **T5.3**: Implement unit tests in `tests/test_matcher.py` (exact match, alternative CWE, $\pm 10$ accepted, $\pm 11$ rejected, multi-line, missing coordinates, 1-to-1 max cardinality, input shuffle determinism, clean PR FPs, extra findings FPs, missing GT FNs).
- [x] **T5.4**: Implement unit tests in `tests/test_dispatcher.py` (Config A static-only, B LLM-only, C hybrid no context, D full hybrid, stage error propagation).
- [x] **T5.5**: Run `pytest` and `ruff` checks.
- [x] **T5.6**: Update `Project Documents/devlog.md` (Session 22), `AI_hand_off.md`, and generate final report.
