#!/usr/bin/env python3
"""Execute Configuration A (Static-Analysis Baseline) on the 17 Ground-Truth-Verified Pilot Cases.

Frozen Methodology Reference:
- FR-03: Deterministic static analysis (Ruff 0.16.10 + Semgrep CE 1.180.0) with suppression isolation.
- FR-09: Experimental evaluation mode with locked +-10 lines tolerance and primary partial-run scoring.
- Zero Retrospective Tuning: This run is executed once against the frozen ruleset manifest without tuning.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from auditor.dataset.pilot_loader import load_pilot_cases_from_json
from auditor.matcher.engine import OfflineEvaluationMatcher
from auditor.models.config import AuditConfiguration
from auditor.models.finding import PredictedFinding
from auditor.models.ground_truth import BenchmarkCase
from auditor.models.request import AuditRequest
from auditor.models.result import AuditStatus
from auditor.orchestration.dispatcher import ConfigurationDispatcher
from auditor.static_analysis.engine import StaticAnalysisEngine

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_RESULTS_DIR = REPO_ROOT / "data" / "results"
RESULTS_FILE = DATA_RESULTS_DIR / "config_a_pilot_run.json"

DATA_RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def resolve_case_repo_path(case: BenchmarkCase) -> Path:
    """Resolve the authentic upstream Git repository location on disk."""
    scratch = REPO_ROOT / "scratch" / "upstream_repos"
    pilot_audit = scratch / "pilot_audit"

    repo_map = {
        "tornadoweb/tornado": pilot_audit / "tornadoweb_tornado",
        "tiangolo/fastapi": pilot_audit / "tiangolo_fastapi",
        "pallets/jinja": pilot_audit / "pallets_jinja",
        "django/django": pilot_audit / "django_django",
        "tortoise/tortoise-orm": pilot_audit / "tortoise_tortoise-orm",
        "aio-libs/aiohttp": pilot_audit / "aio-libs_aiohttp",
        "encode/starlette": pilot_audit / "encode_starlette",
        "jpadilla/pyjwt": pilot_audit / "jpadilla_pyjwt",
        "lepture/authlib": pilot_audit / "lepture_authlib",
        "jupyterhub/jupyterhub": pilot_audit / "jupyterhub_jupyterhub",
        "zulip/zulip": pilot_audit / "zulip_zulip",
        "Kludex/python-multipart": scratch / "cand_0008",
        "pallets/werkzeug": scratch / "cand_0020",
        "paramiko/paramiko": scratch / "cand_0026",
        "scrapy/scrapy": scratch / "scrapy_scrapy",
    }

    # Direct map
    if case.repository in repo_map and repo_map[case.repository].exists():
        repo = repo_map[case.repository]
        # Check if the commit exists in this repo
        res = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-e", f"{case.commit_hash}^{{commit}}"],
            capture_output=True,
        )
        if res.returncode == 0:
            return repo

    # Candidate specific folder fallback
    cand_folder = scratch / case.case_id.lower().replace("-", "_")
    if cand_folder.exists():
        res = subprocess.run(
            ["git", "-C", str(cand_folder), "cat-file", "-e", f"{case.commit_hash}^{{commit}}"],
            capture_output=True,
        )
        if res.returncode == 0:
            return cand_folder

    raise FileNotFoundError(
        f"Could not locate upstream git repository containing commit {case.commit_hash} for {case.case_id}"
    )


def extract_target_file_content(repo_path: Path, commit_hash: str, target_file: str) -> str:
    """Extract authentic file content from Git object store at exact commit revision."""
    res = subprocess.run(
        ["git", "-C", str(repo_path), "show", f"{commit_hash}:{target_file}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if res.returncode != 0:
        raise RuntimeError(f"Failed to extract {target_file} at {commit_hash} from {repo_path}: {res.stderr}")
    return res.stdout


class BenchmarkDiffProvider:
    """Mock diff provider returning the target file path and minimal diff for benchmarking."""

    def __init__(self, target_file: str):
        self.target_file = target_file

    def get_diff(self, request: AuditRequest) -> tuple[str, list[str]]:
        return f"--- a/{self.target_file}\n+++ b/{self.target_file}\n", [self.target_file]


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute Configuration A benchmark or individual case.")
    parser.add_argument(
        "--case-id", type=str, help="Specific case ID to run (e.g., CAND-0006). If omitted, runs all verified cases."
    )
    parser.add_argument(
        "--output", type=str, help="Output JSON path. If omitted, defaults to data/results/config_a_pilot_run.json."
    )
    args = parser.parse_args()

    output_file = Path(args.output).resolve() if args.output else RESULTS_FILE

    print("================================================================================")
    print("PHASE 3B — CONFIGURATION A PILOT BENCHMARK RUN")
    print("Frozen Ruleset: Ruff 0.16.10 (88 rules) + Semgrep CE 1.180.0 (198 rules)")
    print("Scoring Policy: Primary (failed runs = 0 findings), Locked +-10 Lines Window")
    print("================================================================================\n")

    all_cases = load_pilot_cases_from_json(only_verified=True)
    if args.case_id:
        cases = [c for c in all_cases if c.case_id == args.case_id]
        if not cases:
            raise ValueError(f"Case ID '{args.case_id}' not found among verified pilot cases.")
        print(f"Loaded 1 specific case: {args.case_id}\n")
    else:
        cases = all_cases
        print(f"Loaded {len(cases)} GROUND_TRUTH_VERIFIED pilot cases.\n")

    static_engine = StaticAnalysisEngine()
    matcher = OfflineEvaluationMatcher(tolerance_lines=10)

    predictions_by_case: dict[str, list[PredictedFinding]] = {}
    run_records: list[dict[str, Any]] = []

    start_total_time = time.time()

    for idx, case in enumerate(cases, 1):
        target_file = case.defects[0].file_path if case.defects else ""
        print(f"[{idx:02d}/17] Running {case.case_id} ({case.repository})...")
        print(f"       Commit: {case.commit_hash[:10]} | Target: {target_file}")

        repo_path = resolve_case_repo_path(case)
        content = extract_target_file_content(repo_path, case.commit_hash, target_file)

        case_start = time.time()

        # Run inside isolated benchmark workspace for this case
        with tempfile.TemporaryDirectory(prefix=f"bench_{case.case_id}_") as tmpdir:
            tmp_root = Path(tmpdir)
            target_path = tmp_root / target_file
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")

            diff_provider = BenchmarkDiffProvider(target_file)
            dispatcher = ConfigurationDispatcher(
                diff_provider=diff_provider,
                static_engine=static_engine,
            )

            req = AuditRequest(
                request_id=f"bench-configA-{case.case_id}",
                repository_id=case.repository,
                configuration=AuditConfiguration.A,
                workspace_path=str(tmp_root),
                base_commit="HEAD~1",
                head_commit=case.commit_hash,
            )

            run_result = dispatcher.dispatch(req)

        case_duration = time.time() - case_start

        # Primary scoring policy: failed runs contribute zero findings
        if run_result.status != AuditStatus.SUCCESS:
            print(f"       [RUN FAILED]: {run_result.error_message}. Assigning 0 findings per FR-09.")
            case_findings: list[PredictedFinding] = []
        else:
            case_findings = run_result.findings

        predictions_by_case[case.case_id] = case_findings

        # Evaluate case against GT
        case_eval = matcher.evaluate_case(case, case_findings)

        print(
            f"       Emitted {len(case_findings)} finding(s) | TP={case_eval.true_positives} | FP={case_eval.false_positives} | FN={case_eval.false_negatives} ({case_duration:.2f}s)"
        )
        for pair in case_eval.matched_pairs:
            print(
                f"         * MATCHED: {pair.defect_id} with finding {pair.finding_id} ({pair.matched_cwe}, direct={pair.is_direct_overlap})"
            )

        run_records.append(
            {
                "case_id": case.case_id,
                "repository": case.repository,
                "commit_hash": case.commit_hash,
                "target_file": target_file,
                "category_id": case.defects[0].category_id if case.defects else None,
                "primary_cwe": case.defects[0].primary_cwe if case.defects else None,
                "gt_loci": [[d.start_line, d.end_line] for d in case.defects],
                "execution_status": run_result.status.value,
                "duration_seconds": round(case_duration, 3),
                "emitted_findings_count": len(case_findings),
                "findings": [f.model_dump() for f in case_findings],
                "evaluation": case_eval.model_dump(),
            }
        )

    total_duration = time.time() - start_total_time

    # Evaluate full batch
    aggregate_metrics, per_case_results = matcher.evaluate_batch(cases, predictions_by_case)

    output_payload = {
        "benchmark_run_metadata": {
            "configuration": "A",
            "configuration_name": "Configuration A — Deterministic Static Analysis Baseline",
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_cases": len(cases),
            "total_duration_seconds": round(total_duration, 3),
            "tools": {
                "ruff": {"version": "0.16.10", "linters": ["flake8-bandit", "flake8-bugbear", "pyflakes"]},
                "semgrep": {"version": "1.180.0", "edition": "Community Edition (CE)", "rules_count": 198},
            },
            "tolerance_window": "+-10 lines",
            "suppression_isolation": True,
        },
        "aggregate_metrics": aggregate_metrics.model_dump(),
        "cases": run_records,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    print("\n================================================================================")
    print("CONFIG A BENCHMARK EVALUATION RESULTS SUMMARY")
    print("================================================================================")
    print(f"Total Cases Evaluated:       {len(cases)}")
    print(f"Total Ground-Truth Defects:  {aggregate_metrics.total_ground_truth_defects}")
    print(f"Total Predictions Emitted:   {aggregate_metrics.total_predictions}")
    print(f"True Positives (TP):         {aggregate_metrics.true_positives}")
    print(f"False Positives (FP):        {aggregate_metrics.false_positives}")
    print(f"False Negatives (FN):        {aggregate_metrics.false_negatives}")
    p_str = (
        f"{aggregate_metrics.precision * 100:.2f}%" if aggregate_metrics.precision is not None else "UNDEFINED (N/A)"
    )
    r_str = f"{aggregate_metrics.recall * 100:.2f}%" if aggregate_metrics.recall is not None else "UNDEFINED (N/A)"
    f1_str = f"{aggregate_metrics.f1_score * 100:.2f}%" if aggregate_metrics.f1_score is not None else "UNDEFINED (N/A)"
    print(f"Aggregate Precision:         {p_str}")
    print(f"Aggregate Recall:            {r_str}")
    print(f"Aggregate F1 Score:          {f1_str}")
    print(f"Total Benchmark Latency:     {total_duration:.2f}s")
    print(f"Report Output File:          {output_file}")
    print("================================================================================\n")


if __name__ == "__main__":
    main()
