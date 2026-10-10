# Phase 5D: Forensic Reconstruction and Reconciliation Report

**Workspace:** `D:\Khai Van\KhaiVan Data\CODE\AI_Code_Auditor_Thesis1`  
**Date:** October 10, 2026  
**Status:** COMPLETED — 100% PARITY CONFIRMED  
**Audit Artifact:** `data/results/abcd_reconciliation_audit.json`  
**Adjudication Packet:** `Project Documents/dataset/adjudication_packet_bcd_v2.md` (`data/results/adjudication_packet_bcd_v2.json`)

---

## 1. Executive Summary

Phase 5D conducted a comprehensive forensic audit of the historical benchmark records across Configurations A, B, C, and D.
All calculations were performed offline and derived directly from the immutable JSON result artifacts using the unchanged `OfflineEvaluationMatcher(tolerance_lines=10)` with Kuhn bipartite matching.

Key outcomes:
1. **100% Metric Parity Confirmed:** Every single per-case True Positive, False Positive, and False Negative stored in the result artifacts is bitwise reproduced by the unchanged matcher.
2. **Headline Totals Validated:**
   - Config A (18 cases): TP = 3, FP = 126, FN = 20 (Precision = 2.33%, Recall = 13.04%, F1 = 3.95%)
   - Config B (18 cases): TP = 6, FP = 94, FN = 17 (Precision = 6.00%, Recall = 26.09%, F1 = 9.76%)
   - Config C (18 cases): TP = 8, FP = 87, FN = 15 (Precision = 8.42%, Recall = 34.78%, F1 = 13.56%) [CAND-0008 failed under FR-09]
   - Config D (18 cases): TP = 7, FP = 85, FN = 16 (Precision = 7.61%, Recall = 30.43%, F1 = 12.17%) [CAND-0020, 0026, 0033 failed under FR-09]
3. **Paired 17-Case Comparison (Excluding CAND-0008):**
   - In Config B, CAND-0008 contributes exactly **15 FPs** (not 8).
   - Thus, Config B has **79 FPs** on the 17 completed cases ($94 - 15 = 79$).
   - Config C has **87 FPs** on the 17 completed cases.
   - On matched completed cases, static finding augmentation caused an increase of **+8 False Positives** (from 79 to 87).
4. **Common-Completed 14-Case Subset:**
   - Completed cases: CAND-0001, 0002, 0006, 0007, 0009, 0014, 0015, 0017, 0019, 0021, 0025, 0027, 0031, 0032 (19 GT defects).
   - Config B: TP = 5, FP = 60, FN = 14 (P = 7.69%, R = 26.32%, F1 = 11.90%)
   - Config C: TP = 7, FP = 66, FN = 12 (P = 9.59%, R = 36.84%, F1 = 15.22%)
   - Config D: TP = 7, FP = 69, FN = 12 (P = 9.21%, R = 36.84%, F1 = 14.74%)
   - Config D achieved identical recall to Config C ($36.84\%$).
5. **CAND-0007 Chunking and Matching Resolved:**
   - Both Configs B, C, and D processed CAND-0007 using the identical syntax-aware 2-chunk plan (Chunk 1: lines 1-405, Chunk 2: lines 408-1101).
   - The stored match in Config C and D is on lines **182-184 / 184-184**, directly overlapping GT defect `CAND-0007-DEF-1` (lines 182-184). The earlier mention of lines "207-248" was an obsolete diagnostic draft note.
6. **False-Positive Category Attribution:**
   - The benchmark schema attributes False Positives to cases (the target file evaluated), not by parsing the model's reported category ID (since hallucinations frequently misclassify weaknesses). Under case-based attribution, Config D Category 6 has 18 FPs (CAND-0031: 8, CAND-0032: 10). The previously cited "34 FPs" was a transcription error that conflated the number of Category 6 GT defects/metrics.

---

## 2. Auditable Per-Case Reconciliation Table

| Case ID | Cat | GT | Config A (TP/FP/FN) | Config B (TP/FP/FN) | Config C (TP/FP/FN) | Config D (TP/FP/FN) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **CAND-0001** | 1 | 1 | OK (1 / 8 / 0) | OK (0 / 6 / 1) | OK (0 / 6 / 1) | OK (0 / 7 / 1) |
| **CAND-0002** | 1 | 1 | OK (0 / 22 / 1) | OK (0 / 7 / 1) | OK (0 / 7 / 1) | OK (0 / 6 / 1) |
| **CAND-0007** | 2 | 1 | OK (0 / 25 / 1) | OK (0 / 5 / 1) | OK (1 / 7 / 0) | OK (1 / 8 / 0) |
| **CAND-0009** | 2 | 2 | OK (1 / 6 / 1) | OK (1 / 6 / 1) | OK (0 / 8 / 2) | OK (0 / 9 / 2) |
| **CAND-0014** | 3 | 2 | OK (1 / 1 / 1) | OK (0 / 1 / 2) | OK (0 / 2 / 2) | OK (0 / 1 / 2) |
| **CAND-0017** | 3 | 1 | OK (0 / 0 / 1) | OK (1 / 0 / 0) | OK (1 / 0 / 0) | OK (1 / 1 / 0) |
| **CAND-0019** | 4 | 2 | OK (0 / 16 / 2) | OK (1 / 5 / 1) | OK (2 / 5 / 0) | OK (2 / 4 / 0) |
| **CAND-0021** | 4 | 1 | OK (0 / 5 / 1) | OK (1 / 4 / 0) | OK (1 / 5 / 0) | OK (1 / 4 / 0) |
| **CAND-0025** | 5 | 1 | OK (0 / 4 / 1) | OK (0 / 6 / 1) | OK (0 / 5 / 1) | OK (0 / 5 / 1) |
| **CAND-0027** | 5 | 1 | OK (0 / 0 / 1) | OK (0 / 0 / 1) | OK (0 / 0 / 1) | OK (0 / 0 / 1) |
| **CAND-0031** | 6 | 2 | OK (0 / 8 / 2) | OK (0 / 7 / 2) | OK (0 / 7 / 2) | OK (0 / 8 / 2) |
| **CAND-0032** | 6 | 2 | OK (0 / 13 / 2) | OK (0 / 8 / 2) | OK (0 / 9 / 2) | OK (0 / 10 / 2) |
| **CAND-0006** | 1 | 1 | OK (0 / 2 / 1) | OK (1 / 3 / 0) | OK (1 / 3 / 0) | OK (1 / 5 / 0) |
| **CAND-0008** | 2 | 1 | OK (0 / 8 / 1) | OK (0 / 15 / 1) | FAIL (0 / 0 / 1) | OK (0 / 16 / 1) |
| **CAND-0015** | 3 | 1 | OK (0 / 0 / 1) | OK (0 / 2 / 1) | OK (1 / 2 / 0) | OK (1 / 1 / 0) |
| **CAND-0020** | 4 | 1 | OK (0 / 0 / 1) | OK (1 / 1 / 0) | OK (1 / 1 / 0) | FAIL (0 / 0 / 1) |
| **CAND-0026** | 5 | 1 | OK (0 / 7 / 1) | OK (0 / 16 / 1) | OK (0 / 17 / 1) | FAIL (0 / 0 / 1) |
| **CAND-0033** | 6 | 1 | OK (0 / 1 / 1) | OK (0 / 2 / 1) | OK (0 / 3 / 1) | FAIL (0 / 0 / 1) |
| **Total** | | **23** | **3 / 126 / 20** | **6 / 94 / 17** | **8 / 87 / 15** | **7 / 85 / 16** |

---

## 3. Human Adjudication Packet (Version 2.0)

Packet regenerated to:
- JSON: `data/results/adjudication_packet_bcd_v2.json`
- Markdown: `Project Documents/dataset/adjudication_packet_bcd_v2.md`

Summary:
- **Unique Ground-Truth Defects Represented:** 9
- **Total Matched Rows:** 21 (Config B: 6, Config C: 8, Config D: 7)
- **Zero Config A Rows Included** (B/C/D evaluation only)
- **Review Flags Documented:**
  - `CAND-0007-DEF-1`: Model reported JSON parsing DoS (CWE-400) directly overlapping lines 182-184 of CSRF defect (CWE-352 / CWE-20). Flagged for human adjudication.
  - `CAND-0019-DEF-2`: Config B matched at lines 577-579 against GT lines 574-576 (distance = 1 line, valid under $\pm 10$ tolerance). Config C and D matched with direct overlap.

---

## 4. Benchmark Chunk Census by Tier

Direct evaluation of the chunk plan via `SourceChunker(token_budget=16000)` and per-configuration chunk records establishes the following exact census across the 18 canonical benchmark cases:

| Tier | Strategy | Cases Count | Chunks / Case | Total Chunks | Case IDs |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Tier 1** | Single-pass whole file ($\le 16,000$ tokens) | **13** | 1 | **13** | CAND-0001, CAND-0002, CAND-0006, CAND-0014, CAND-0015, CAND-0017, CAND-0019, CAND-0021, CAND-0025, CAND-0027, CAND-0031, CAND-0033, CAND-0020 |
| **Tier 2** | Syntax-aware AST chunking | **4** | 2 | **8** | CAND-0007, CAND-0008, CAND-0009, CAND-0032 |
| **Tier 3** | Sliding window ($N=100$ lines overlap) | **1** | 3 | **3** | CAND-0026 |
| **Total** | | **18** | — | **24** | |

*Census Arithmetic:* $13\text{ (Tier 1)} + 4\text{ (Tier 2)} + 1\text{ (Tier 3)} = \mathbf{18\text{ cases}}$, and $13 \times 1 + 4 \times 2 + 1 \times 3 = 13 + 8 + 3 = \mathbf{24\text{ planned chunks}}$.
(Note: An earlier preliminary working note erroneously stated "14 Tier 1 + 6 Tier 2 + 3 Tier 3 + 2 CAND-0007 chunks", which double-counted CAND-0007 and conflated chunk counts with case counts. The verified breakdown above is mathematically sound and matches the recorded run logs.)

---

## 5. CAND-0007 Source Coverage & Chunk Boundaries

Inspection of the pre-fix snapshot `fastapi/routing.py` at commit `90120dd6e8` across chunk boundaries confirms:
- **Chunk 1:** Lines 1 to 405 (ends at line 405: closing parenthesis `        )` of `get()` route decorator helper).
- **Chunk Boundary Lines 406–407:**
  - Line 406: empty blank line (`""`).
  - Line 407: empty blank line (`""`).
  - Neither line contains executable code, comments, or docstrings.
- **Chunk 2:** Lines 408 to 1101 (starts at line 408: `class APIRouter(routing.Router):`).
- **Conclusion:** Zero executable code or comments were omitted between Chunks 1 and 2. The historical 2-chunk syntax plan provides complete, lossless coverage of all source code in `fastapi/routing.py`. The historical chunk plan remains unchanged.

---

## 6. Config D Repository Context Budget Compliance Qualification

In Configuration D, repository-level context retrieval was capped at $B_{\text{context}} \le 4,000$ tokens per chunk.
- **Runtime Enforcement:** Context packing in `src/auditor/llm/context_retriever.py` enforced a conservative character-based heuristic:
  $$\text{tokens} \approx \left\lfloor \frac{\text{len}(\text{rendered\_context\_item})}{3.2} \right\rfloor + 20$$
- **Heuristic Audit:** Across all 24 chunks in the Config D pilot run, the heuristic context token estimate ranged from 607 to 3,924 tokens, staying strictly within the 4,000-token cap.
- **Measurement Limitation & Verification Qualification:** Exact tokenization via Claude's official tokenizer was not recorded or retained per isolated context excerpt during the pilot execution. Therefore, while recorded heuristic estimates complied with the budget ceiling, **exact 4,000-token compliance cannot be verified from retained context-only measurements**. No network or tokenizer API calls were made to fabricate post-hoc token measurements.
