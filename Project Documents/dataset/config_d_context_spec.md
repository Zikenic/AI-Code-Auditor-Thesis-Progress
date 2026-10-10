# Configuration D Context Retrieval Specification (Version 1.0)

**Configuration:** D (Full Hybrid Auditor: Static Analysis + Repository Context)  
**Context Token Budget:** $B_{\text{context}} \le 4,000$ tokens  
**Retrieval Backend:** Option B — AST Symbol-Graph Traversal + Lexical / BM25 Inverted Index  
**Primary Scoring Rule:** LLM predictions only (never merge raw static findings or retrieved context into predictions)  
**Ground-Truth Shield:** Strict (No defect loci, advisory text, patch diffs, fix commits, or subsequent history)

---

## 1. Overview & Objective

Configuration D evaluates the marginal effect of adding repository-level context to the static-augmented LLM review (Configuration C). The central research question is whether providing cross-file context (such as class definitions, imported helpers, base classes, and authentication/authorization helper functions) alters detection performance, particularly for Category 5 (Authentication) and Category 6 (Authorization) defects.

---

## 2. Retrieval Backend Rationale & Environment Constraints

Host environment inspection confirmed:
1. Docker Engine is offline, precluding ephemeral PostgreSQL/pgvector containers.
2. The local gateway endpoint (`http://localhost:20128/v1/embeddings`) does not support embedding generation with current API credentials (returning `401 Unauthorized`).
3. Native Git trees at the exact pre-fix commits ($C_{\text{buggy}}$) are fully preserved in `scratch/upstream_repos/` for all 18 benchmark cases.

**Selected Backend (Option B):**
- **Tier 1 (AST Symbol Graph):** Deterministic resolution of imported symbols, enclosing classes, base classes, and cross-file method definitions referenced within the target chunk.
- **Tier 2 (Lexical / BM25 Inverted Index):** Lexical search across pre-fix repository Python modules for queries derived strictly from active chunk symbols.

No claims of semantic embedding or pgvector vector retrieval are made for this implementation.

---

## 3. Pre-Fix Repository Index Construction

For each benchmark case, indexing is restricted exclusively to the pre-fix repository snapshot at commit $C_{\text{buggy}}$:

1. **Extraction Scope:** Only `.py` files present in `git ls-tree -r $C_{\text{buggy}}` are indexed.
2. **Exclusions:**
   - Test suites (`tests/`, `testing/`, `test_*.py`, `*_test.py`).
   - Build artifacts, virtual environments, migrations, docs (`docs/`, `doc/`, `migrations/`).
   - Post-fix commits, PR diffs, commit messages, and Git logs.
   - Advisory texts, benchmark case notes, and ground-truth annotations.
3. **Reproducibility Identifier:** For each case, record the exact pre-fix commit SHA and the number of indexed files and symbols.

---

## 4. Query Construction Rules (Zero-Leakage Invariant)

Queries must be derived **mechanically and exclusively** from the active code chunk:

1. **Imported Symbols:** Symbols imported via `from <module> import <name>` or `import <module>`.
2. **Referenced Identifiers:** Calls to external functions, instantiated classes, and attribute accesses (`obj.method()`) detected in the chunk's AST.
3. **Enclosing Structure:** The class name and base classes of any class definition present in the chunk.
4. **Prohibited Information:**
   - Zero access to ground-truth defect IDs, line ranges, or CWE labels.
   - Zero access to fix commits, commit diffs, or remediation keywords.
   - Zero category-specific branching or tuning.

---

## 5. Candidate Ranking, Deduplication, and Budgeting

1. **Target Chunk Exclusion (Hard Rule):** The active target chunk is **strictly excluded** from retrieved context.
2. **Same-File Exclusion:** Slices from the same target file are excluded unless they represent an imported or base-class definition located outside the chunk, with a preference for cross-file context.
3. **Deduplication:** Candidates are deduplicated by `[file_path, start_line, end_line]`.
4. **Ranking Hierarchy:**
   - Priority 1: Direct AST resolution of symbols imported and called in the chunk.
   - Priority 2: Base class definitions of classes defined in the chunk.
   - Priority 3: BM25 lexical matches for chunk function and class names.
5. **Budget Cap ($B_{\text{context}} \le 4,000$ tokens):**
   - Each excerpt is formatted as:
     ```text
     --- CONTEXT: path/to/file.py (Lines start to end) ---
     <line_number>: <code>
     ```
   - Candidates are added in rank order until adding the next item would exceed 4,000 tokens.
   - Any remaining candidates are omitted, and `[Notice: N additional context excerpts omitted]` is recorded.

---

## 6. Prompt Assembly & Provenance Logging

The retrieved context is injected into the single designated section `{repository_context_section}` in `config_d_prompt_v1.md`.

For every chunk, the result artifact records:
- Retrieved excerpt list: `[file_path, start_line, end_line, token_count, query_symbol]`.
- Total retrieved context tokens.
- Omitted candidate count.
- Index provenance: commit SHA and file count.
