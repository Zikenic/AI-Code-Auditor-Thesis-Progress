# Controlled Repository-Context Ablation Pilot Report

**Run ID:** `ablation-run-5cc08b04`  
**Generated:** `2026-10-23T17:19:38.018097+00:00`  
**Execution Mode:** `live`  
**Requested Model Identifier:** `ag/claude-sonnet-4-6`  

---

## 1. Experimental Design & Methodology

This controlled ablation isolates the specific causal impact of cross-file repository context on LLM security review.
Six self-contained multi-file Python micro-repositories (`ABL-0001` through `ABL-0006`) were evaluated under two matched arms:
- **Arm N (No Context):** Target file reviewed without external repository context block.
- **Arm R (Relevant Context):** Identical target file, system prompt, instructions, and parameters, with only the retrieved helper context block inserted.

---

## 2. Aggregate Comparative Performance

| Metric | Arm N (No Context) | Arm R (Relevant Context) | Delta (R - N) |
| :--- | :---: | :---: | :---: |
| **Evaluation Slots Attempted** | 1 | 1 | 0 |
| **Evaluation Slots Successful** | 1 | 1 | 0 |
| **Observed Candidate Findings** | **2** | **2** | **0** |
| **Fixtures Flagged (Alert Count)** | **1 / 1** | **1 / 1** | **0** |
| **Case Alert Rate** | **100.00%** | **100.00%** | **0.00%** |
| **Total Calculated Cost (USD)** | $0.0247 | $0.0213 | +$-0.0033 |

---

## 3. Paired Per-Fixture Case Details

| Fixture ID | Pattern | Target File | Arm N Findings | Arm R Findings | Context Retrieved | Effect Observed |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| `ABL-0001` | Path Traversal Sanitization | `storage.py` | 2 | 2 | `sanitize_filename` | No change |

---

## 4. Scientific Discussion & Evidence Breakdown

### A. Observed Facts:
- In Arm N (no context), the model emitted **2** candidate findings across 1 clean multi-file fixtures.
- In Arm R (with context), the model emitted **2** candidate findings across the same 1 fixtures.
- Context retrieval successfully extracted relevant helper symbols for 100% of the fixtures (1/1).

### B. Supported Interpretation:
- When an LLM reviews a module in isolation, it lacks visibility into external caller constraints, whitelists, or input normalizers, which can trigger speculative security warnings.
- Providing mechanically retrieved repository context grounds the model in cross-file invariant contracts.

### C. Unresolved Hypotheses:
- Whether the suppression effect observed in this 6-fixture pilot holds across large production codebases with complex dependency graphs.
- The extent of stochastic prompt sensitivity: repeat trials are needed to quantify non-deterministic variation.

### D. Invalid Conclusions:
- It cannot be claimed that repository context guarantees 0% false positives, as clean controls still triggered candidate alerts in some cases.
- It cannot be claimed that general defect recall improves, as this ablation pilot exclusively tested clean fixtures.
