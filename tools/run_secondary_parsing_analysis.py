"""Lenient repair and secondary parsing evaluation across Config B, C, and D."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from auditor.dataset.pilot_loader import load_pilot_cases_from_json
from auditor.llm.deduplication import deduplicate_findings
from auditor.llm.parser import ConfigBResponseParser
from auditor.matcher.engine import OfflineEvaluationMatcher
from auditor.models.ground_truth import BenchmarkCase

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_B_FILE = REPO_ROOT / "data" / "results" / "config_b_pilot_run.json"
CONFIG_C_FILE = REPO_ROOT / "data" / "results" / "config_c_pilot_run.json"
CONFIG_D_FILE = REPO_ROOT / "data" / "results" / "config_d_pilot_run.json"


def lenient_repair_json(raw_text: str) -> str:
    r"""Repair unescaped backslashes in JSON strings.

    In valid JSON, a backslash is either:
    1. An escape sequence: \", \\, \/, \b, \f, \n, \r, \t, or \uXXXX
    2. Any literal single backslash not followed by these characters.
    """
    clean = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
    clean = re.sub(r"```\s*$", "", clean.strip(), flags=re.MULTILINE)

    # State-machine character-by-character backslash repair inside strings
    out = []
    in_string = False
    i = 0
    n = len(clean)

    while i < n:
        char = clean[i]
        if char == '"':
            # Check if escaped
            escaped = False
            k = i - 1
            while k >= 0 and clean[k] == "\\":
                escaped = not escaped
                k -= 1
            if not escaped:
                in_string = not in_string
            out.append(char)
            i += 1
        elif char == "\\" and in_string:
            # Lookahead next char
            if i + 1 < n:
                nxt = clean[i + 1]
                if nxt in ['"', "\\", "/", "b", "f", "n", "r", "t"]:
                    out.append("\\")
                    out.append(nxt)
                    i += 2
                elif nxt == "u" and i + 5 < n and all(c in "0123456789abcdefABCDEF" for c in clean[i + 2 : i + 6]):
                    out.append(clean[i : i + 6])
                    i += 6
                else:
                    # Invalid escape sequence: turn \ into \\
                    out.append("\\\\")
                    i += 1
            else:
                out.append("\\\\")
                i += 1
        else:
            out.append(char)
            i += 1

    return "".join(out)


def reparse_and_score(config_path: Path, config_name: str) -> dict[str, Any]:
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)

    cases_dict: dict[str, BenchmarkCase] = {c.case_id: c for c in load_pilot_cases_from_json(only_verified=True)}
    matcher = OfflineEvaluationMatcher(tolerance_lines=10)
    parser = ConfigBResponseParser()

    repaired_cases_count = 0
    repaired_chunks_count = 0
    secondary_cases = []

    for case_data in data["cases"]:
        cid = case_data["case_id"]
        target_file = case_data["target_file"]
        benchmark_case = cases_dict[cid]
        chunk_telemetry = case_data.get("telemetry", {}).get("chunk_telemetry", [])

        case_findings = []
        case_failed = False
        repaired_in_this_case = False
        # Check FR-09: if the case was marked failed due to incomplete chunks or HTTP errors
        if case_data.get("execution_status") == "failed" and not case_data.get("failure_reason", "").startswith(
            "Parsing failed"
        ):
            case_failed = True
        elif not chunk_telemetry:
            case_failed = True
        else:
            for ct in chunk_telemetry:
                raw_resp = ct.get("raw_response", "")
                if not raw_resp:
                    case_failed = True
                    break

                # First try raw
                try:
                    findings = parser.parse_response(
                        raw_text=raw_resp,
                        expected_file_path=target_file,
                        total_file_lines=10000,
                        chunk_start_line=1,
                        chunk_end_line=10000,
                    )
                    case_findings.extend(findings)
                except Exception:
                    # Apply lenient repair
                    repaired_text = lenient_repair_json(raw_resp)
                    try:
                        findings = parser.parse_response(
                            raw_text=repaired_text,
                            expected_file_path=target_file,
                            total_file_lines=10000,
                            chunk_start_line=1,
                            chunk_end_line=10000,
                        )
                        case_findings.extend(findings)
                        repaired_chunks_count += 1
                        repaired_in_this_case = True
                    except Exception:
                        case_failed = True
                        break

        if repaired_in_this_case:
            repaired_cases_count += 1

        if case_failed:
            final_findings = []
            status = "failed"
        else:
            final_findings = deduplicate_findings(case_findings)
            status = "success"

        case_eval = matcher.evaluate_case(benchmark_case, final_findings)
        secondary_cases.append(
            {
                "case_id": cid,
                "status": status,
                "emitted_findings": len(final_findings),
                "tp": case_eval.true_positives,
                "fp": case_eval.false_positives,
                "fn": case_eval.false_negatives,
            }
        )

    tot_tp = sum(c["tp"] for c in secondary_cases)
    tot_fp = sum(c["fp"] for c in secondary_cases)
    tot_fn = sum(c["fn"] for c in secondary_cases)
    p = (tot_tp / (tot_tp + tot_fp)) * 100 if (tot_tp + tot_fp) > 0 else 0.0
    r = (tot_tp / (tot_tp + tot_fn)) * 100 if (tot_tp + tot_fn) > 0 else 0.0
    f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0

    return {
        "config": config_name,
        "repaired_cases": repaired_cases_count,
        "repaired_chunks": repaired_chunks_count,
        "successful_cases": sum(1 for c in secondary_cases if c["status"] == "success"),
        "failed_cases": sum(1 for c in secondary_cases if c["status"] == "failed"),
        "total_emitted": sum(c["emitted_findings"] for c in secondary_cases),
        "tp": tot_tp,
        "fp": tot_fp,
        "fn": tot_fn,
        "precision": round(p, 2),
        "recall": round(r, 2),
        "f1": round(f1, 2),
        "cases": secondary_cases,
    }


def main():
    print("================================================================================")
    print("SECONDARY PARSING ANALYSIS — LENIENT ESCAPE REPAIR ACROSS B, C, AND D")
    print("================================================================================")

    res_b = reparse_and_score(CONFIG_B_FILE, "Config B")
    res_c = reparse_and_score(CONFIG_C_FILE, "Config C")
    res_d = reparse_and_score(CONFIG_D_FILE, "Config D")

    print(
        f"{'Config':<10} | {'Repaired Cases':<14} | {'Succ/Fail':<10} | {'Emitted':<8} | {'TP':<4} | {'FP':<4} | {'FN':<4} | {'Precision':<10} | {'Recall':<10} | {'F1':<8}"
    )
    print("-" * 96)
    for res in [res_b, res_c, res_d]:
        succ_str = f"{res['successful_cases']}/{res['failed_cases']}"
        print(
            f"{res['config']:<10} | {res['repaired_cases']:<14} | {succ_str:<10} | {res['total_emitted']:<8} | {res['tp']:<4} | {res['fp']:<4} | {res['fn']:<4} | {res['precision']:<9.2f}% | {res['recall']:<9.2f}% | {res['f1']:<7.2f}%"
        )

    print("\nCase-by-Case Status in Secondary Analysis:")
    print("Case ID    | Config B (TP/FP) | Config C (TP/FP) | Config D (TP/FP)")
    print("-" * 65)
    for i in range(18):
        cb = res_b["cases"][i]
        cc = res_c["cases"][i]
        cd = res_d["cases"][i]
        cid = cb["case_id"]
        sb = f"[{cb['status']}] {cb['tp']}/{cb['fp']}"
        sc = f"[{cc['status']}] {cc['tp']}/{cc['fp']}"
        sd = f"[{cd['status']}] {cd['tp']}/{cd['fp']}"
        print(f"{cid:<10} | {sb:<16} | {sc:<16} | {sd:<16}")


if __name__ == "__main__":
    main()
