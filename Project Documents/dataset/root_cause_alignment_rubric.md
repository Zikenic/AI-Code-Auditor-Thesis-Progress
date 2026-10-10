# Secondary Root-Cause Alignment Evaluation Rubric

**Version:** 1.0 (Frozen)  
**Date:** October 9, 2026  
**Status:** FROZEN METHODOLOGICAL RUBRIC  
**Role in Evaluation:** Secondary exploratory analysis. The official primary evaluation metric remains strictly governed by the locked bipartite matcher (CWE matching + $\pm 10$ line tolerance window). Semantic labels assigned under this rubric **never overwrite, modify, or replace official TP/FP/FN counts**.

---

## 1. Motivation and Methodological Role

The primary benchmark methodology awards a True Positive (TP) whenever a predicted finding satisfies:
1. File path match.
2. Primary or acceptable alternative CWE match.
3. Coordinate proximity within a $\pm 10$ line window of the canonical defect locus.

As empirically demonstrated in Phase 3B.1, deterministic static tools can trigger proximity matches on incidental, adjacent syntax (e.g., an internal state assertion or class inheritance declaration) that completely miss the actual defect's logic.

This rubric establishes a standardized, reproducible protocol for conducting a **secondary qualitative assessment** to determine whether a mechanically matched finding genuinely understands and identifies the causal root fault of the vulnerability.

---

## 2. Classification Labels and Decision Criteria

Every prediction that scores as a mechanical True Positive under the primary evaluation matcher is assigned exactly one of the following three mutually exclusive labels:

### 2.1 `ROOT_CAUSE_ALIGNED`
- **Definition:** The finding substantive explanation identifies the specific causal mechanism or omitted logic responsible for the ground-truth defect.
- **Criteria:**
  1. The finding message or reasoning points to the specific flaw described in the ground-truth defect record (e.g., missing validation, unescaped identifier, out-of-order state transition).
  2. The proposed remediation or description would correct or mitigate the target vulnerability.
  3. The match is causal, not merely incidental.

### 2.2 `PROXIMITY_ONLY`
- **Definition:** The finding satisfies the primary mechanical matcher criteria (correct CWE and line proximity within $\pm 10$ lines) but identifies an unrelated programming construct, generic code smell, or adjacent code element that does not explain the target defect.
- **Criteria:**
  1. The flagged code construct is syntactically near the defect locus, but its logic is not the cause of the vulnerability.
  2. Resolving the flagged issue would leave the actual ground-truth vulnerability completely unmitigated.
  3. Examples include generic assertions (`assert`), broad exception catches, or pattern matches on standard library wrappers.

### 2.3 `INDETERMINATE`
- **Definition:** The finding text or diagnostic payload is too vague, ambiguous, or truncated to reliably ascertain whether the tool/model identified the causal root fault.
- **Criteria:**
  1. Extremely generic alert messages (e.g. "Input validation error" or "Security issue detected") lacking reasoning or contextual specifics.
  2. The explanation contains mixed assertions where causal understanding cannot be confirmed or refuted.

---

## 3. Boundary Cases and Decision Rules

1. **Overbroad or Vague Finding Rule:**
   If a finding emits a generic high-level CWE alert (e.g., `CWE-20: Improper Input Validation`) without explaining *what* input is untrusted or *how* it bypasses controls, it must be labeled **`INDETERMINATE`**, not `ROOT_CAUSE_ALIGNED`.
2. **Adjacent Construct Rule:**
   If a tool flags a line within $\pm 10$ lines of the defect locus for a generic risk (e.g., `assert` statement or `logging.info`), but the actual vulnerability resides in adjacent algorithmic or parsing logic, the finding must be labeled **`PROXIMITY_ONLY`**.
3. **Partial Semantic Understanding:**
   If a finding correctly identifies the vulnerable function and untrusted data flow, but slightly mischaracterizes the precise exploitation vector, it qualifies as **`ROOT_CAUSE_ALIGNED`** provided the identified flaw corresponds to the defect.

---

## 4. Rater and Blinding Procedure

### 4.1 Rater Protocol
- **Default Rater:** Single student-rater (Bùi Vạn Khải).
- **Rater Discipline:** Because evaluations are conducted by a single rater, results will be reported transparently as **single-rater exploratory labels**. No claim of inter-rater reliability, Cohen's Kappa, or independent consensus will be made unless a qualified second rater independently assesses the dataset.

### 4.2 Blinding and Sanitization Protocol
To minimize evaluation bias when assessing findings across Configurations A, B, C, and D:
1. **Provenance Stripping:** All direct identifying metadata must be scrubbed from the assessment view:
   - Tool name (e.g., `ruff`, `semgrep`).
   - Rule ID (e.g., `S101`, `extends-custom-expression`).
   - Configuration ID (e.g., `CONFIG_A`, `CONFIG_B`).
   - LLM model/provider headers (e.g., `gpt-4o`, `claude-3-5-sonnet`).
2. **Assessment Record Schema:** The rater is presented with a sanitized JSON/Markdown record containing only:
   - `case_id` (e.g. `CAND-0001`).
   - `ground_truth_summary` (official description from `pilot_cases.json`).
   - `finding_locus` (predicted line number range).
   - `finding_cwe` (predicted CWE).
   - `finding_text` (normalized finding title and description).
3. **Order Randomization:** Assessment records from different configurations must be shuffled pseudo-randomly before rating.
4. **Known Blinding Limitations:** Standard linter outputs (e.g., succinct bandit messages like `Use of assert detected`) possess distinct phrasing patterns that cannot be fully disguised from LLM prose. This limitation is acknowledged transparently.

---

## 5. Reference Examples

### 5.1 Observed Examples: `PROXIMITY_ONLY` (From Phase 3B Config A Baseline)
The following are real, observed benchmark findings from `data/results/config_a_pilot_run.json`:

1. **CAND-0001 (`tornadoweb/tornado`) — Observed `PROXIMITY_ONLY`**
   - *Ground Truth:* Locus [390, 394], `CWE-670`. Missing chunk size limit / Transfer-Encoding handling bug causing HTTP request smuggling.
   - *Flagged Code (L385):* `assert self._read_finished`
   - *Finding Text:* "Ruff [S101]: Use of assert detected"
   - *Label Rationale:* The finding flags an internal state machine assertion. Fixing or removing this assert does not fix the HTTP Transfer-Encoding parsing vulnerability.

2. **CAND-0009 (`pallets/jinja`) — Observed `PROXIMITY_ONLY`**
   - *Ground Truth:* Locus [292, 293], `CWE-79`. Improper XML/HTML attribute name escaping allowing XSS in template AST nodes.
   - *Flagged Code (L303):* `return markupsafe.Markup(buf.getvalue())`
   - *Finding Text:* "Ruff [S704]: Potential XSS: markupsafe.Markup used"
   - *Label Rationale:* Flags the return wrapper instantiation. The vulnerability was lack of attribute key sanitization at lines 292–293.

3. **CAND-0014 (`django/django`) — Observed `PROXIMITY_ONLY`**
   - *Ground Truth:* Locus [225, 236], `CWE-89`. SQL Injection in `TruncBase.__init__` due to unquoted truncation parameters.
   - *Flagged Code (L206–216):* `class Now(Func): ...`
   - *Finding Text:* "Semgrep [extends-custom-expression]: Class extends custom expression"
   - *Label Rationale:* Flags class declaration extending `Func`. Does not identify the SQL injection in `TruncBase.__init__`.

### 5.2 Constructed Illustration: `ROOT_CAUSE_ALIGNED`
*(Constructed illustration for guideline clarification; not an observed benchmark finding)*
- *Target Defect:* CAND-0007 (FastAPI, missing Content-Type validation allowing CSRF via JSON body).
- *Illustrative Finding Text:* "Request body parsed as JSON via `await request.json()` without verifying that incoming Content-Type header matches `application/json`. Allows cross-origin browsers to submit simple text/plain requests that are treated as authenticated JSON payloads."
- *Label Rationale:* Directly identifies the exact vulnerability mechanism and exploitation path.

### 5.3 Constructed Illustration: `INDETERMINATE`
*(Constructed illustration for guideline clarification; not an observed benchmark finding)*
- *Target Defect:* CAND-0021 (Starlette, Path Traversal via `os.path.commonprefix`).
- *Illustrative Finding Text:* "Potential Path Traversal: Path verification logic on line 172 might be unsafe."
- *Label Rationale:* Flags the general category and line, but fails to explain why `os.path.commonprefix` is flawed or how the boundary check fails. Lacks sufficient substance to confirm causal understanding.

---

## 6. Immutability & Versioning Contract
This rubric is version 1.0 (Frozen). It will not be retroactively modified after Configuration B or C results are observed. Any future refined analysis must be designated as a separate, clearly labeled exploratory study (e.g. Version 2.0-exploratory).
