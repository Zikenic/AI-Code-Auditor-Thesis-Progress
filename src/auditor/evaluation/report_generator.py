"""Report and Artifact Generator for AI Code Auditor Benchmark Evaluations.

Produces:
1. Machine-readable JSON export (case-level details, finding annotations, metrics).
2. Tabular CSV summary comparing Configurations A, B, C, and D.
3. Comprehensive Markdown evaluation report adhering to academic and thesis standards.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from auditor.evaluation.manifest import BenchmarkManifest
from auditor.evaluation.metrics import CaseEvaluationDetail, ConfigurationMetrics


class EvaluationReportGenerator:
    """Generates structured evaluation reports in JSON, CSV, and Markdown formats."""

    def __init__(
        self,
        manifest: BenchmarkManifest,
        metrics_by_config: dict[str, ConfigurationMetrics],
        details_by_config: dict[str, list[CaseEvaluationDetail]],
        run_metadata: dict[str, Any] | None = None,
    ):
        self.manifest = manifest
        self.metrics_by_config = metrics_by_config
        self.details_by_config = details_by_config
        self.run_metadata = run_metadata or {}
        self.generated_at = datetime.now(UTC).isoformat()

    def generate_json_artifact(self, output_path: Path) -> Path:
        """Export full machine-readable evaluation results to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": {
                "generated_at": self.generated_at,
                "dataset_description": self.manifest.description,
                "total_cases": len(self.manifest.cases),
                "verified_cases": len(self.manifest.get_verified_buggy_cases()),
                "clean_cases": len(self.manifest.get_clean_cases()),
                "unknown_cases": len(self.manifest.get_unknown_cases()),
                **self.run_metadata,
            },
            "configurations": {
                cfg: metrics.model_dump() for cfg, metrics in self.metrics_by_config.items()
            },
            "case_level_details": {
                cfg: [d.model_dump() for d in details] for cfg, details in self.details_by_config.items()
            },
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        return output_path

    def generate_csv_summary(self, output_path: Path) -> Path:
        """Export tabular comparison summary across configurations to CSV."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "Configuration",
            "Cases Attempted",
            "Cases Successful",
            "Buggy Cases",
            "Clean Cases Attempted",
            "Clean Cases Successful",
            "Clean Mocked Count",
            "True Positives",
            "Confirmed False Positives",
            "Unadjudicated Findings",
            "Historical Naive FP",
            "False Negatives",
            "Historical Naive Precision (%)",
            "Confirmed Precision (%)",
            "Confirmed Precision Status",
            "Recall (%)",
            "Historical Naive F1 Score (%)",
            "Clean Case FPR",
            "Clean Case FPR Status",
            "Clean Case FPR Note",
            "Defect Detection Rate (%)",
            "Common Subset TP (14 cases)",
            "Common Subset FP (14 cases)",
            "Common Subset F1 (%)",
            "Failed Runs",
            "Partial Runs",
            "Static Preserved (C)",
            "Confirmed Triage (C)",
            "Likely FP Triage (C)",
            "Additional Candidates (C)",
            "Delta TP over C (D)",
            "Delta FP over C (D)",
            "Duration (s)",
            "Cost (USD)",
        ]

        rows = []
        for cfg, m in sorted(self.metrics_by_config.items()):
            naive_p_str = f"{m.historical_naive_precision * 100:.2f}" if m.historical_naive_precision is not None else "N/A"
            conf_p_str = f"{m.confirmed_precision * 100:.2f}" if m.confirmed_precision is not None else "N/A"
            r_str = f"{m.recall * 100:.2f}" if m.recall is not None else "N/A"
            f1_str = f"{m.f1_score * 100:.2f}" if m.f1_score is not None else "N/A"

            if m.clean_case_fpr_status == "unavailable_mock":
                fpr_str = "Unavailable (mock LLM)"
            elif m.clean_case_false_positive_rate is not None:
                fpr_str = f"{m.clean_case_false_positive_rate * 100:.2f}%"
            else:
                fpr_str = "N/A"

            det_str = f"{m.defect_case_detection_rate * 100:.2f}" if m.defect_case_detection_rate is not None else "N/A"

            c_sub = m.common_subset_metrics or {}
            c_tp = c_sub.get("true_positives", "N/A")
            c_fp = c_sub.get("false_positives", "N/A")
            c_f1 = f"{c_sub.get('f1_score', 0) * 100:.2f}" if c_sub.get("f1_score") is not None else "N/A"

            rows.append({
                "Configuration": f"Config {cfg}",
                "Cases Attempted": m.cases_attempted or m.total_cases_evaluated,
                "Cases Successful": m.cases_successful or (m.total_cases_evaluated - m.failed_runs_count),
                "Buggy Cases": m.buggy_cases_evaluated,
                "Clean Cases Attempted": m.clean_cases_attempted,
                "Clean Cases Successful": m.clean_cases_successful,
                "Clean Mocked Count": m.clean_cases_mocked_count,
                "True Positives": m.true_positives,
                "Confirmed False Positives": m.confirmed_false_positives,
                "Unadjudicated Findings": m.unadjudicated_predictions,
                "Historical Naive FP": m.false_positives,
                "False Negatives": m.false_negatives,
                "Historical Naive Precision (%)": naive_p_str,
                "Confirmed Precision (%)": conf_p_str,
                "Confirmed Precision Status": m.confirmed_precision_status or "N/A",
                "Recall (%)": r_str,
                "Historical Naive F1 Score (%)": f1_str,
                "Clean Case FPR": fpr_str,
                "Clean Case FPR Status": m.clean_case_fpr_status or "N/A",
                "Clean Case FPR Note": m.clean_case_fpr_note or "",
                "Defect Detection Rate (%)": det_str,
                "Common Subset TP (14 cases)": c_tp,
                "Common Subset FP (14 cases)": c_fp,
                "Common Subset F1 (%)": c_f1,
                "Failed Runs": m.failed_runs_count,
                "Partial Runs": m.partial_runs_count,
                "Static Preserved (C)": m.static_findings_preserved if cfg in ("C", "D") else "N/A",
                "Confirmed Triage (C)": m.static_findings_confirmed if cfg in ("C", "D") else "N/A",
                "Likely FP Triage (C)": m.static_findings_likely_fp if cfg in ("C", "D") else "N/A",
                "Additional Candidates (C)": m.additional_llm_candidates if cfg in ("C", "D") else "N/A",
                "Delta TP over C (D)": m.incremental_tp_over_c if m.incremental_tp_over_c is not None else "N/A",
                "Delta FP over C (D)": m.incremental_fp_over_c if m.incremental_fp_over_c is not None else "N/A",
                "Duration (s)": f"{m.total_duration_seconds:.2f}",
                "Cost (USD)": f"${m.total_cost_usd:.4f}" if m.total_cost_usd is not None else "N/A",
            })

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return output_path

    def generate_markdown_report(self, output_path: Path) -> Path:
        """Export academic and evidence-grounded Markdown report."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = [
            "# AI Code Auditor — Experimental Evaluation & Provenance Integrity Report",
            "",
            f"**Generated:** `{self.generated_at}`  ",
            f"**Execution Mode:** `{self.run_metadata.get('mode', 'offline')}`  ",
            f"**Git Commit Baseline:** `{self.run_metadata.get('commit_hash', 'current-head')}`  ",
            "**Evaluation Matching Tolerance:** `+-10 lines (ADR-10 locked methodology)`  ",
            "",
            "---",
            "",
            "## 1. Provenance Audit & Scientific Validity Clarifications",
            "",
            "### Origin of Benchmark Numbers & Gateway Metadata:",
            "- **Config A (Deterministic Static Analysis):** Ruff 0.16.10 + Semgrep CE 1.180.0. 100% reproducible locally without network or API dependencies.",
            "- **Config B (LLM Only):** Historical pilot run executed on 2026-10-09 against gateway identifier `ag/claude-sonnet-4-6`. 18/18 defective cases completed successfully.",
            "- **Config C (Static + LLM Triage):** Historical pilot run executed on 2026-10-10 against gateway identifier `ag/claude-sonnet-4-6`. 17/18 defective cases completed successfully; CAND-0008 failed due to LLM JSON escape parsing error.",
            "- **Config D (Contextual Hybrid):** Historical pilot run executed on 2026-10-10 against gateway identifier `ag/claude-sonnet-4-6`. 15/18 defective cases completed successfully; 3 cases failed (CAND-0020 parsing error; CAND-0026 and CAND-0033 due to upstream HTTP 503 reset).",
            "- **Gateway Model Identity Limitation:** The requested and configured model identifier is `ag/claude-sonnet-4-6`. The serving gateway reports this alias; specific underlying backend versioning or routing beyond this identifier cannot be independently verified from gateway HTTP responses alone.",
            "- **Live Execution Transport Evidence:** During live execution of clean controls, an internal 500 error occurred at step 11547 and was recovered via client-side exponential retry. While case outcomes completed as success, the execution transport history was retry-recovered rather than failure-free.",
            "- **Inference Cost Accounting:** Config B incurred $0.2308 and Config C incurred $0.1989 across 18 reviews. Config D cost was unrecorded during live execution due to telemetry omission. The total known live cost lower bound is $0.4297 (Config D cost is additional).",
            "- **Offline Evaluation Mode:** In offline evaluation mode, historical pilot outputs are loaded from frozen run artifacts (`data/results/config_*_pilot_run.json`). No live models were re-queried for pilot cases.",
            "",
            "### Scientific Validity Rules & Metric Eligibility:",
            "1. **Isolation of Mock Validation:** In offline mode, the 18 clean controls for Configurations B, C, and D are evaluated using `MockEvaluationLlmClient`. Mock outputs validate test pipeline mechanics and schema compliance, but **MUST NEVER be reported or interpreted as empirical model false-positive rates (0.00%)**. Therefore, Clean-case FPR for Config B, C, and D is strictly classified as **Unavailable (Mock)**.",
            "2. **Ground-Truth Completeness Distinction:**",
            "   - **Historical Pilot Cases (`CAND-0001` to `CAND-0033`):** Annotation completeness is **`partial`**. Each candidate is a real repository file where only the primary target CVE/defect locus was annotated. Unmatched predictions outside the locus are classified as **unadjudicated candidate findings**, not confirmed false positives.",
            "   - **Clean Control Cases (`CTRL-0001` to `CTRL-0018`):** Annotation completeness is **`exhaustive`**. Each control is a small, self-contained deterministic Python fixture audited for Categories 1–6 with 0 SAST alerts. Findings emitted on clean controls represent observed candidate alerts on code intended to be clean, which have not undergone third-party manual panel adjudication.",
            "3. **Config A Clean Specificity Caveat:** Config A achieves 0.00% warning rate on the 18 clean controls via deterministic SAST. This is valid evidence of tool specificity on this curated sample, but must not be generalized to arbitrary production repositories.",
            "",
            "---",
            "",
            "## 2. Benchmark Dataset Composition",
            "",
            "| Dataset Partition | Cases Count | Ground Truth Defects | Annotation Completeness | Description |",
            "| :--- | :---: | :---: | :---: | :--- |",
            f"| **Verified Defective Pilot Cases** | `{len(self.manifest.get_verified_buggy_cases())}` | 23 defects | `partial` | Sourced from popular Python repositories (Django, FastAPI, Tornado, etc.) |",
            f"| **Verified Clean Control Cases** | `{len(self.manifest.get_clean_cases())}` | 0 defects | `exhaustive` | Deterministic, secure Python fixtures paired with pilot categories |",
            f"| **Total Cases in Manifest** | `{len(self.manifest.cases)}` | 23 defects | Mixed | Full benchmark cohort for evaluation |",
            "",
            "---",
            "",
            "## 3. Aggregate Performance Metrics Comparison",
            "",
            "| Metric | Config A (Static) | Config B (LLM Only) | Config C (Hybrid) | Config D (Repo Context) |",
            "| :--- | :---: | :---: | :---: | :---: |",
        ]

        def fmt_pct(val: float | None) -> str:
            return f"**{val * 100:.2f}%**" if val is not None else "N/A"

        def fmt_status(m: ConfigurationMetrics | None) -> str:
            if not m:
                return "N/A"
            return f"{m.failed_runs_count} failed / {m.partial_runs_count} partial"

        def get_m(cfg: str) -> ConfigurationMetrics | None:
            return self.metrics_by_config.get(cfg)

        ma = get_m("A")
        mb = get_m("B")
        mc = get_m("C")
        md = get_m("D")

        def fmt_clean_fpr(m: ConfigurationMetrics | None) -> str:
            if not m:
                return "N/A"
            if m.clean_case_fpr_status == "unavailable_mock":
                return "**Unavailable** *(mock LLM client)*"
            if m.clean_case_false_positive_rate is not None:
                return f"**{m.clean_case_false_positive_rate * 100:.2f}%** *(curated sample)*"
            return "N/A"

        def fmt_conf_prec(m: ConfigurationMetrics | None) -> str:
            if not m:
                return "N/A"
            if m.confirmed_precision_status == "unavailable_unadjudicated":
                return "**Unavailable** *(partial ground truth)*"
            if m.confirmed_precision is not None:
                return f"**{m.confirmed_precision * 100:.2f}%**"
            return "N/A"

        def fmt_conf_fp(m: ConfigurationMetrics | None) -> str:
            if not m:
                return "N/A"
            tag = " *(mock)*" if m.clean_cases_mocked_count > 0 else ""
            return f"{m.confirmed_false_positives}{tag}"

        lines.extend([
            f"| **Cases Attempted** | {ma.cases_attempted if ma else 'N/A'} | {mb.cases_attempted if mb else 'N/A'} | {mc.cases_attempted if mc else 'N/A'} | {md.cases_attempted if md else 'N/A'} |",
            f"| **Cases Successful** | {ma.cases_successful if ma else 'N/A'} | {mb.cases_successful if mb else 'N/A'} | {mc.cases_successful if mc else 'N/A'} | {md.cases_successful if md else 'N/A'} |",
            f"| **Execution Status / Failures** | {fmt_status(ma)} | {fmt_status(mb)} | {fmt_status(mc)} | {fmt_status(md)} |",
            f"| **True Positives (TP)** | {ma.true_positives if ma else 'N/A'} | {mb.true_positives if mb else 'N/A'} | {mc.true_positives if mc else 'N/A'} | {md.true_positives if md else 'N/A'} |",
            f"| **Observed Clean-Control Findings (Unadjudicated)** | {fmt_conf_fp(ma)} | {fmt_conf_fp(mb)} | {fmt_conf_fp(mc)} | {fmt_conf_fp(md)} |",
            f"| **Unadjudicated Predictions (Pilot Cases)** | {ma.unadjudicated_predictions if ma else 'N/A'} | {mb.unadjudicated_predictions if mb else 'N/A'} | {mc.unadjudicated_predictions if mc else 'N/A'} | {md.unadjudicated_predictions if md else 'N/A'} |",
            f"| **Historical Naive FP (Total Unmatched)** | {ma.false_positives if ma else 'N/A'} | {mb.false_positives if mb else 'N/A'} | {mc.false_positives if mc else 'N/A'} | {md.false_positives if md else 'N/A'} |",
            f"| **False Negatives (FN)** | {ma.false_negatives if ma else 'N/A'} | {mb.false_negatives if mb else 'N/A'} | {mc.false_negatives if mc else 'N/A'} | {md.false_negatives if md else 'N/A'} |",
            f"| **Clean-Control Case Alert Rate** | {fmt_clean_fpr(ma)} | {fmt_clean_fpr(mb)} | {fmt_clean_fpr(mc)} | {fmt_clean_fpr(md)} |",
            f"| **Recall (Defect Level)** | {fmt_pct(ma.recall if ma else None)} | {fmt_pct(mb.recall if mb else None)} | {fmt_pct(mc.recall if mc else None)} | {fmt_pct(md.recall if md else None)} |",
            f"| **Defect Case Detection Rate** | {fmt_pct(ma.defect_case_detection_rate if ma else None)} | {fmt_pct(mb.defect_case_detection_rate if mb else None)} | {fmt_pct(mc.defect_case_detection_rate if mc else None)} | {fmt_pct(md.defect_case_detection_rate if md else None)} |",
            f"| **Confirmed Precision** | {fmt_conf_prec(ma)} | {fmt_conf_prec(mb)} | {fmt_conf_prec(mc)} | {fmt_conf_prec(md)} |",
            f"| **Historical Naive Precision (Proxy)** | {fmt_pct(ma.historical_naive_precision if ma else None)} | {fmt_pct(mb.historical_naive_precision if mb else None)} | {fmt_pct(mc.historical_naive_precision if mc else None)} | {fmt_pct(md.historical_naive_precision if md else None)} |",
            f"| **Historical Naive F1 Score (Proxy)** | {fmt_pct(ma.f1_score if ma else None)} | {fmt_pct(mb.f1_score if mb else None)} | {fmt_pct(mc.f1_score if mc else None)} | {fmt_pct(md.f1_score if md else None)} |",
        ])

        # Common subset comparison / Cohort separation
        total_buggy_in_eval = sum(m.buggy_cases_evaluated for m in (ma, mb, mc, md) if m)
        if total_buggy_in_eval == 0:
            lines.extend([
                "",
                "---",
                "",
                "## 4. Defective Pilot Cohort vs Clean Control Separation",
                "",
                "The current evaluation run evaluated exclusively the **18 clean control fixtures** (`CTRL-0001` to `CTRL-0018`). All 18 cases completed successfully across all 4 configurations without execution failure.",
                "",
                "To maintain rigorous ground-truth separation and prevent conflating clean-case alert rates with defect recall, historical defect recall from the canonical common 14-case defective pilot benchmark (19 gold defects across cases where all configurations completed) is documented below as a distinct historical baseline:",
                "",
                "| Metric (14 Common Defective Cases) | Config A (Static) | Config B (LLM Only) | Config C (Hybrid) | Config D (Repo Context) |",
                "| :--- | :---: | :---: | :---: | :---: |",
                "| **True Positives (TP)** | 3 | 5 | 7 | 7 |",
                "| **False Negatives (FN)** | 16 | 14 | 12 | 12 |",
                "| **Defect-Level Recall (%)** | **15.79%** (3/19) | **26.32%** (5/19) | **36.84%** (7/19) | **36.84%** (7/19) |",
                "| **Historical Naive FP (Unadjudicated)** | 110 | 60 | 66 | 69 |",
                "| **Historical Naive Precision (%)** | **2.65%** | **7.69%** | **9.59%** | **9.21%** |",
                "| **Historical Naive F1 Score (%)** | **4.55%** | **11.90%** | **15.22%** | **14.74%** |",
                "",
                "**Defensible Scientific Observations on Common Subset:**",
                "- **Defect Recall Parity:** Configurations C and D both detect exactly 7/19 defects (**36.84% recall**). Repository context in Config D produced zero additional true positives over Config C.",
                "- **Prediction Volume & Noise:** Config D produced 69 candidate predictions compared to 66 for Config C (delta +3).",
                "- **Reliability & Overhead:** In historical defective evaluation, Config D suffered 3 pipeline failures (1 schema syntax error, 2 HTTP 503 resets) vs 1 failure for Config C, with ~3.2x longer execution duration.",
                "- **Scientific Adjudication Requirement:** Declaring Config C definitively superior in precision or Config D worse requires expert adjudication of the 66 vs 69 candidate findings.",
            ])
        else:
            lines.extend([
                "",
                "---",
                "",
                "## 4. Common Successfully Evaluated Subset Comparison",
                "",
                "To prevent failure bias from skewing comparisons, the table below evaluates exclusively the cases that succeeded across all 4 configurations in this evaluation run:",
                "",
                "| Metric (Common Cases) | Config A (Static) | Config B (LLM Only) | Config C (Hybrid) | Config D (Repo Context) |",
                "| :--- | :---: | :---: | :---: | :---: |",
            ])

            def get_common(cfg: str, field: str) -> str:
                m = get_m(cfg)
                if not m or not m.common_subset_metrics:
                    return "N/A"
                val = m.common_subset_metrics.get(field)
                if val is None:
                    return "N/A"
                if "f1" in field or "precision" in field or "recall" in field:
                    return f"**{val * 100:.2f}%**"
                return str(val)

            lines.extend([
                f"| **True Positives (TP)** | {get_common('A', 'true_positives')} | {get_common('B', 'true_positives')} | {get_common('C', 'true_positives')} | {get_common('D', 'true_positives')} |",
                f"| **Historical Naive FP (Unadjudicated)** | {get_common('A', 'false_positives')} | {get_common('B', 'false_positives')} | {get_common('C', 'false_positives')} | {get_common('D', 'false_positives')} |",
                f"| **False Negatives (FN)** | {get_common('A', 'false_negatives')} | {get_common('B', 'false_negatives')} | {get_common('C', 'false_negatives')} | {get_common('D', 'false_negatives')} |",
                f"| **Recall (%)** | {get_common('A', 'recall')} | {get_common('B', 'recall')} | {get_common('C', 'recall')} | {get_common('D', 'recall')} |",
                f"| **Historical Naive Precision (%)** | {get_common('A', 'precision')} | {get_common('B', 'precision')} | {get_common('C', 'precision')} | {get_common('D', 'precision')} |",
                f"| **Historical Naive F1 Score (%)** | {get_common('A', 'f1_score')} | {get_common('B', 'f1_score')} | {get_common('C', 'f1_score')} | {get_common('D', 'f1_score')} |",
            ])

        if mc:
            lines.extend([
                "",
                "---",
                "",
                "## 5. Configuration C Detailed Triage Analysis",
                "",
                "| Triage Metric | Count | Description |",
                "| :--- | :---: | :--- |",
                f"| **Static Findings Preserved** | `{mc.static_findings_preserved}` | All detected static findings retained without silent deletion |",
                f"| **Confirmed by LLM** | `{mc.static_findings_confirmed}` | Static findings verified as reachable, genuine defects |",
                f"| **Triaged Likely False Positives** | `{mc.static_findings_likely_fp}` | Static findings refuted with technical rationale |",
                f"| **Inconclusive Findings** | `{mc.static_findings_inconclusive}` | Findings lacking sufficient local context to confirm |",
                f"| **Additional LLM Candidates** | `{mc.additional_llm_candidates}` | Novel defects flagged by LLM not detected by static analysis |",
                f"| **Correct False-Positive Refutations** | `{mc.triage_correct_fp_count}` | Static FPs successfully identified and triaged by LLM |",
            ])

        # Section 6: Case-by-Case Provenance & Metric Eligibility Matrix
        lines.extend([
            "",
            "---",
            "",
            "## 6. Case-by-Case Provenance & Metric Eligibility Matrix",
            "",
            "| Case ID | Partition | GT Completeness | Config A Prov | Config B Prov | Config C Prov | Config D Prov | Recall Eligible | Clean FPR Eligible |",
            "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |",
        ])

        # Build lookup for case details
        detail_lookup: dict[tuple[str, str], CaseEvaluationDetail] = {}
        for cfg, dlist in self.details_by_config.items():
            for d in dlist:
                detail_lookup[(cfg, d.case_id)] = d

        for mcase in self.manifest.cases:
            cid = mcase.case_id
            part_str = "Pilot" if mcase.is_buggy else "Clean"
            comp_str = mcase.annotation_completeness.value

            def get_prov_cell(cfg: str, case_id: str = cid) -> str:
                det = detail_lookup.get((cfg, case_id))
                if not det:
                    return "N/A"
                st = det.execution_status
                pr = det.provenance
                return f"`{pr}` ({st})"

            pa = get_prov_cell("A")
            pb = get_prov_cell("B")
            pc = get_prov_cell("C")
            pd = get_prov_cell("D")

            # Check if any LLM config ran with real models
            has_real_llm = any(p.startswith("`real_model`") for p in (pb, pc, pd))
            rec_elig = "Yes" if mcase.is_buggy else "No (clean)"
            if mcase.is_buggy:
                clean_fpr_elig = "No (buggy)"
            elif has_real_llm:
                clean_fpr_elig = "Yes (evaluated configs)"
            else:
                clean_fpr_elig = "Config A only"

            lines.append(f"| `{cid}` | {part_str} | `{comp_str}` | {pa} | {pb} | {pc} | {pd} | {rec_elig} | {clean_fpr_elig} |")

        lines.extend([
            "",
            "---",
            "",
            "## 7. Threats to Scientific Validity & Thesis Readiness",
            "",
            "1. **Mock Validation vs Empirical False-Positive Rate:** In offline mode, clean controls use mock LLM responses to verify test mechanics, which cannot establish empirical false-positive rates. When live API inference is run, empirical clean-case false-positive rates are directly observed and reported on the curated sample.",
            "2. **Context Scope on Standalone Fixtures:** Clean control fixtures are independent Python files located in `data/fixtures/clean_controls/`. When Config D builds an AST index over this directory, it indexes sibling test fixtures rather than an integrated repository. In multiple cases (`CTRL-0003`, `CTRL-0013`, `CTRL-0016`), retrieved context was completely empty. In other cases (`CTRL-0001`, `CTRL-0012`), context consisted of accidental symbol collisions across unrelated fixtures. Therefore, the observed reduction in candidate findings from 8 in Config C to 4 in Config D cannot be causally attributed to caller/repository context; it reflects prompt structure and stochastic variance.",
            "3. **Unadjudicated Negative Space & Observed Clean Findings:** Historical pilot cases only annotate the primary bug locus (`partial` completeness). Observed findings outside the locus and findings emitted on clean controls represent candidate alerts that have not undergone independent third-party manual panel adjudication.",
            "4. **Telemetry Accounting & Cost Lower Bound:** Config D execution telemetry did not record USD cost. The total known live inference cost across Config B and Config C is $0.4297, which serves as an empirical lower bound for the live experiment.",
            "5. **Gateway Model Identity Limitation:** The model identifier `ag/claude-sonnet-4-6` is an endpoint alias. Specific backend versioning beyond this alias cannot be independently verified from gateway HTTP responses alone.",
            "6. **Thesis Recommendation:** Present Config C as the primary defensible hybrid architecture. Report clean-control alert rates alongside pilot recall, explicitly separate clean specificity from defect recall, and avoid causal claims regarding repository context on standalone fixtures.",
        ])

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        return output_path
