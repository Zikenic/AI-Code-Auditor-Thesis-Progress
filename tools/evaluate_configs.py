#!/usr/bin/env python3
"""Reproducible Evaluation CLI for AI Code Auditor Benchmark Configurations (A/B/C/D).

Usage examples:
    # Run offline comparison across all 4 configurations on the 18 pilot cases
    python tools/evaluate_configs.py --configs A B C D --mode offline

    # Run single-case evaluation for Config C
    python tools/evaluate_configs.py --configs C --cases CAND-0001 --mode offline

    # Run bounded live model smoke test (requires authorized local gateway)
    python tools/evaluate_configs.py --configs C --cases CAND-0001 --mode live --smoke-test
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from pathlib import Path
from typing import Any

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from auditor.evaluation.manifest import load_benchmark_manifest  # noqa: E402
from auditor.evaluation.metrics import ConfigurationMetrics, compute_configuration_metrics  # noqa: E402
from auditor.evaluation.report_generator import EvaluationReportGenerator  # noqa: E402
from auditor.evaluation.runner import EvaluationRunner  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_configs")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reproducible Benchmark Evaluation Harness for AI Code Auditor (Config A/B/C/D)"
    )
    parser.add_argument(
        "--configs",
        nargs="+",
        default=["A", "B", "C", "D"],
        help="List of configurations to evaluate (default: A B C D).",
    )
    parser.add_argument(
        "--cases",
        type=str,
        default="all",
        help="Comma-separated case IDs to evaluate (e.g. 'CAND-0001,CAND-0002') or 'all' (default: all).",
    )
    default_manifest = REPO_ROOT / "data" / "benchmark_manifest.json"
    if not default_manifest.exists():
        default_manifest = REPO_ROOT / "data" / "pilot_cases.json"

    parser.add_argument(
        "--manifest",
        type=Path,
        default=default_manifest,
        help="Path to machine-readable benchmark manifest (default: data/benchmark_manifest.json if available).",
    )
    parser.add_argument(
        "--mode",
        choices=["offline", "dry-run", "live"],
        default="offline",
        help="Execution mode: 'offline' (deterministic fixtures/mock), 'dry-run', or 'live' (local gateway).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "data" / "results",
        help="Output directory for generated evaluation artifacts (default: data/results).",
    )
    parser.add_argument(
        "--tolerance",
        type=int,
        default=10,
        help="Matching line coordinate tolerance in lines (default: 10 per ADR-10).",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Explicit run identifier (default: auto-generated timestamp/uuid).",
    )
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run a bounded single-case live model smoke test (refuses large runs on live mode).",
    )
    parser.add_argument(
        "--allow-clean-controls-live",
        action="store_true",
        help="Explicitly authorize running real-model live inference across clean-control fixtures (max 18 cases, 54 calls).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mode = "offline" if args.mode in ("offline", "dry-run") else "live"
    run_id = args.run_id or f"eval-run-{uuid.uuid4().hex[:8]}"

    logger.info("=== AI Code Auditor — Benchmark Evaluation Harness ===")
    logger.info("Run ID: %s | Mode: %s | Configurations: %s", run_id, mode, args.configs)

    # 1. Load Manifest
    try:
        manifest = load_benchmark_manifest(args.manifest)
        logger.info(
            "Loaded manifest: %d cases (%d verified defective, %d clean, %d unknown)",
            len(manifest.cases),
            len(manifest.get_verified_buggy_cases()),
            len(manifest.get_clean_cases()),
            len(manifest.get_unknown_cases()),
        )
    except Exception as e:
        logger.error("Failed to load benchmark manifest: %s", e)
        return 1

    # 2. Case Selection
    selected_case_ids: list[str] | None = None
    if args.cases.lower() == "clean":
        selected_case_ids = [c.case_id for c in manifest.get_clean_cases()]
        logger.info("Selected all %d clean-control cases for evaluation: %s", len(selected_case_ids), selected_case_ids)
    elif args.cases.lower() != "all":
        selected_case_ids = [c.strip().upper() for c in args.cases.split(",") if c.strip()]
        logger.info("Selected %d cases for evaluation: %s", len(selected_case_ids), selected_case_ids)

    # Safety Guard on Live Mode
    is_authorized_clean_run = (
        args.allow_clean_controls_live
        and selected_case_ids
        and all(c.startswith("CTRL-") for c in selected_case_ids)
        and len(selected_case_ids) <= 18
    )

    if mode == "live" and not args.smoke_test and not is_authorized_clean_run and (not selected_case_ids or len(selected_case_ids) > 2):
        logger.error(
            "LIVE INFERENCE SAFETY GUARD: Running live mode requires --smoke-test (for <= 2 cases) or --allow-clean-controls-live (for <= 18 clean controls)."
        )
        logger.error("To run clean-control evaluation, specify e.g.: --cases clean --mode live --allow-clean-controls-live")
        return 2

    # 3. Instantiate Runner
    try:
        runner = EvaluationRunner(manifest=manifest, mode=mode)
    except Exception as e:
        logger.error("Failed to initialize EvaluationRunner: %s", e)
        return 1

    # 4. Execute Configurations
    metrics_by_config: dict[str, ConfigurationMetrics] = {}
    details_by_config: dict[str, list[Any]] = {}
    run_outputs_by_config: dict[str, Any] = {}
    config_c_baseline: ConfigurationMetrics | None = None

    # Sort configs so C runs before D for delta calculation
    ordered_configs = sorted(args.configs, key=lambda c: (c != "A", c != "B", c != "C", c != "D"))

    for cfg in ordered_configs:
        cfg_upper = cfg.upper()
        logger.info("Executing Configuration %s...", cfg_upper)
        run_output = runner.run_configuration(config=cfg_upper, case_ids=selected_case_ids, run_id=run_id)
        run_outputs_by_config[cfg_upper] = run_output

    # Find common successfully evaluated cases across all executed configurations
    common_case_ids: set[str] | None = None
    if len(ordered_configs) > 1:
        success_sets = []
        for cfg in ordered_configs:
            ro = run_outputs_by_config[cfg.upper()]
            s_set = {cid for cid, st in ro.statuses_by_case.items() if st in ("success", "completed")}
            success_sets.append(s_set)
        if success_sets:
            common_case_ids = set.intersection(*success_sets)
            logger.info("Identified %d common successfully evaluated cases across configurations.", len(common_case_ids))

    # Compute metrics per configuration
    for cfg in ordered_configs:
        cfg_upper = cfg.upper()
        run_output = run_outputs_by_config[cfg_upper]

        # Filter manifest cases for metrics computation
        eval_cases = manifest.cases
        if selected_case_ids:
            eval_cases = [c for c in eval_cases if c.case_id.upper() in selected_case_ids]

        metrics, details = compute_configuration_metrics(
            configuration=cfg_upper,
            manifest_cases=eval_cases,
            predictions_by_case=run_output.predictions_by_case,
            statuses_by_case=run_output.statuses_by_case,
            durations_by_case=run_output.durations_by_case,
            provenance_by_case=run_output.provenance_by_case,
            cost_usd=run_output.cost_usd,
            tolerance_lines=args.tolerance,
            config_c_baseline=config_c_baseline if cfg_upper == "D" else None,
            common_case_ids=common_case_ids,
        )

        if cfg_upper == "C":
            config_c_baseline = metrics

        metrics_by_config[cfg_upper] = metrics
        details_by_config[cfg_upper] = details

    # 5. Output Summary Table
    print("\n" + "=" * 90)
    print("AI CODE AUDITOR — BENCHMARK EVALUATION SUMMARY")
    print("=" * 90)
    print(
        f"{'Config':<10} | {'Cases':<6} | {'TP':<4} | {'Conf FP':<7} | {'Unadj':<5} | {'FN':<4} | {'Clean FPR':<12} | {'Recall':<8} | {'Status'}"
    )
    print("-" * 90)
    for cfg, m in sorted(metrics_by_config.items()):
        rec_str = f"{m.recall * 100:.2f}%" if m.recall is not None else "N/A"
        if m.clean_case_fpr_status == "unavailable_mock":
            clean_fpr_str = "N/A (mock)"
        elif m.clean_case_false_positive_rate is not None:
            tag = "real" if (not m.is_mock_evaluation and cfg != "A") else "det"
            clean_fpr_str = f"{m.clean_case_false_positive_rate * 100:.2f}% ({tag})"
        else:
            clean_fpr_str = "N/A"
        status_str = f"{m.failed_runs_count}F/{m.partial_runs_count}P" if (m.failed_runs_count or m.partial_runs_count) else "OK"
        print(
            f"Config {cfg:<3} | {m.total_cases_evaluated:<6} | {m.true_positives:<4} | {m.confirmed_false_positives:<7} | {m.unadjudicated_predictions:<5} | {m.false_negatives:<4} | {clean_fpr_str:<12} | {rec_str:<8} | {status_str}"
        )
    print("=" * 90 + "\n")

    # 6. Generate Artifacts
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report_gen = EvaluationReportGenerator(
        manifest=manifest,
        metrics_by_config=metrics_by_config,
        details_by_config=details_by_config,
        run_metadata={"run_id": run_id, "mode": mode, "tolerance": args.tolerance},
    )

    json_path = report_gen.generate_json_artifact(args.output_dir / "evaluation_summary.json")
    csv_path = report_gen.generate_csv_summary(args.output_dir / "evaluation_summary.csv")
    md_path = report_gen.generate_markdown_report(args.output_dir / "evaluation_report.md")

    if args.output_dir.resolve() == (REPO_ROOT / "data" / "results").resolve():
        report_gen.generate_markdown_report(REPO_ROOT / "Project Documents" / "reports" / "evaluation_comparison_report.md")
    else:
        doc_report_name = f"{args.output_dir.name}_report.md"
        report_gen.generate_markdown_report(REPO_ROOT / "Project Documents" / "reports" / doc_report_name)

    logger.info("Generated JSON artifact: %s", json_path)
    logger.info("Generated CSV artifact:  %s", csv_path)
    logger.info("Generated Markdown report: %s", md_path)
    logger.info("Evaluation completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
