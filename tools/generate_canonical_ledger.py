"""Generate canonical finding ledger from raw context ablation results.

Enforces strict one-to-one accounting between raw model output items and adjudication entries.
Includes multi-tier denominator evaluation for ABL-0004 (work factor and input bounds).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_RESULTS_PATH = REPO_ROOT / "data" / "results" / "context_ablation_pilot" / "pilot_run" / "ablation_results.json"
LEDGER_JSON_PATH = REPO_ROOT / "data" / "ablation_canonical_ledger.json"
LEDGER_CSV_PATH = REPO_ROOT / "data" / "results" / "context_ablation_pilot" / "canonical_finding_ledger.csv"
SUMMARY_JSON_PATH = REPO_ROOT / "data" / "results" / "context_ablation_pilot" / "ledger_metrics_summary.json"

# Deterministic ground-truth classification data per finding ID
ADJUDICATION_DEFINITIONS = {
    "ABL-0001-N-1": {
        "line": 21,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": "ABL-0001-R-1",
        "peer_match_rationale": "Both arms allege path containment check vulnerability via str(target_path).startswith(str(target_dir)).",
        "source_evidence": "storage.py lines 16-22; validators.py lines 23-33",
        "adjudication_rationale": "clean_name is sanitized by validators.sanitize_filename to eliminate all path separators, null bytes, and traversal components. target_path is strictly a direct child of target_dir; path escape outside the upload directory is physically impossible.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0001-N-2": {
        "line": 16,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": "ABL-0001-R-2",
        "peer_match_rationale": "Both arms critique the possibility of sanitize_filename returning empty or invalid filenames.",
        "source_evidence": "validators.py lines 16-17, 31-32; storage.py line 16",
        "adjudication_rationale": "Without seeing validators.py, Arm N speculates that sanitize_filename could return empty or None. In reality, validators.py explicitly checks if not safe_name and raises ValueError; speculation is refuted by source code.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0001-R-1": {
        "line": 21,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": "ABL-0001-N-1",
        "peer_match_rationale": "Counterpart to ABL-0001-N-1 on path prefix containment check.",
        "source_evidence": "storage.py line 21; validators.py lines 23-33",
        "adjudication_rationale": "Alleges prefix confusion attack (e.g. /uploads matching /uploads_evil). In this fixture, target_path is constructed strictly as target_dir / clean_name where clean_name contains no directory separators or traversal sequences, preventing prefix confusion escape.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0001-R-2": {
        "line": 16,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": "ABL-0001-N-2",
        "peer_match_rationale": "Counterpart to ABL-0001-N-2 on empty sanitized filename.",
        "source_evidence": "validators.py lines 31-33",
        "adjudication_rationale": "Alleges clean_name could be empty or whitespace. validators.py line 31 explicitly validates if not safe_name and raises ValueError. If filename consists only of underscores, it is a valid non-empty file, not target_dir.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0001-R-3": {
        "line": 24,
        "primary_category": "3_plausible_or_unresolved_concern",
        "peer_match_id": None,
        "peer_match_rationale": "Unique to Arm R.",
        "source_evidence": "storage.py lines 24-25",
        "adjudication_rationale": "Alleges TOCTOU symlink race between target_dir.mkdir and open(target_path, 'wb'). Under the documented remote upload threat model, remote callers cannot manipulate server-side filesystem symlinks. Under a local shared-filesystem attacker model, lack of O_NOFOLLOW / O_EXCL is a defense-in-depth consideration.",
        "security_clean_status": "PLAUSIBLE_CONCERN",
    },
    "ABL-0002-N-1": {
        "line": 12,
        "primary_category": "3_plausible_or_unresolved_concern",
        "peer_match_id": "ABL-0002-R-2",
        "peer_match_rationale": "Both arms flag that requesting_user_id is accepted in retrieve_tenant_document signature but not verified.",
        "source_evidence": "documents.py lines 9-14, 25-28",
        "adjudication_rationale": "The function is specifically an endpoint for tenant-level isolation (retrieve_tenant_document). Accepting requesting_user_id without utilizing it is an unused argument (ARG001 / code smell), not an exploitable IDOR flaw since tenant boundaries are fully enforced.",
        "security_clean_status": "PLAUSIBLE_CONCERN",
    },
    "ABL-0002-N-2": {
        "line": 27,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": "ABL-0002-R-1",
        "peer_match_rationale": "Both arms allege that record.get('tenant_id', '') returning an empty string allows tenant isolation to be bypassed.",
        "source_evidence": "documents.py line 27; authz.py lines 17-18",
        "adjudication_rationale": "Alleges empty string fallback bypasses tenant boundary. In authz.py line 17, if not user_tenant_id or not document_tenant_id raises TenantAccessDenied immediately. Fails closed; access is blocked.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0002-N-3": {
        "line": 34,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": None,
        "peer_match_rationale": "Unique to Arm N.",
        "source_evidence": "documents.py lines 25-28, 34",
        "adjudication_rationale": "Alleges unhandled KeyError on record['tenant_id'] at line 34 if tenant_id key is absent. If tenant_id is missing, assert_tenant_boundary on line 25 receives empty string and raises TenantAccessDenied; line 34 is unreachable.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0002-R-1": {
        "line": 27,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": "ABL-0002-N-2",
        "peer_match_rationale": "Counterpart to ABL-0002-N-2 on missing tenant_id check.",
        "source_evidence": "documents.py line 27; authz.py lines 17-19",
        "adjudication_rationale": "Model concedes TenantAccessDenied is raised when tenant_id is empty, then claims 'architectural ambiguity'. There is no code path where a document lacking a valid matching tenant_id can be returned.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0002-R-2": {
        "line": 12,
        "primary_category": "3_plausible_or_unresolved_concern",
        "peer_match_id": "ABL-0002-N-1",
        "peer_match_rationale": "Counterpart to ABL-0002-N-1 on unused requesting_user_id.",
        "source_evidence": "documents.py line 12",
        "adjudication_rationale": "Code quality concern (unused function parameter ARG001); tenant boundary enforcement is sound.",
        "security_clean_status": "PLAUSIBLE_CONCERN",
    },
    "ABL-0003-N-1": {
        "line": 18,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": None,
        "peer_match_rationale": "Suppressed in Arm R when schema_whitelist.py context was provided.",
        "source_evidence": "reports.py line 18; schema_whitelist.py lines 5-10, 22-26",
        "adjudication_rationale": "Arm N assumes validate_table_whitelist is untrusted or bypassable. schema_whitelist.py strictly validates input against an immutable frozenset of 4 static literals; SQL injection on table identifier is impossible.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0003-N-2": {
        "line": 15,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": None,
        "peer_match_rationale": "Suppressed in Arm R when schema_whitelist.py context was provided.",
        "source_evidence": "reports.py line 15; schema_whitelist.py lines 19-24",
        "adjudication_rationale": "Speculates that validate_table_whitelist might return None or empty string. The function raises ValueError on invalid or empty input and never returns None.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0004-N-1": {
        "line": 24,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": None,
        "peer_match_rationale": "Unique to Arm N.",
        "source_evidence": "login_handler.py line 24; rate_limiter.py lines 29-32",
        "adjudication_rationale": "Hallucination. Model claims authentication proceeds after RateLimitExceeded. In Python, raising an unhandled exception immediately halts function execution and unwinds stack; hashing is never reached.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0004-N-2": {
        "line": 32,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": "ABL-0004-R-3",
        "peer_match_rationale": "Both arms flag format/encoding comparison between hex string and stored_hash.",
        "source_evidence": "login_handler.py lines 32, 34",
        "adjudication_rationale": "stored_hash is typed str and derived is a hex str. Returning False on mismatched hash formats safely rejects login; not a security flaw.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0004-N-3": {
        "line": 13,
        "primary_category": "3_plausible_or_unresolved_concern",
        "peer_match_id": None,
        "peer_match_rationale": "Unique to Arm N.",
        "source_evidence": "login_handler.py lines 27-32",
        "adjudication_rationale": "Alleges CPU exhaustion DoS if password_attempt is multi-megabytes. In HMAC (RFC 2104 / FIPS 198-1), keys longer than 64 bytes are hashed once with SHA-256 down to 32 bytes before PBKDF2 loops begin (~7ms overhead for 10MB; PBKDF2 does not hash 10MB on each iteration). However, unbounded string input allocation in memory remains a valid defensive hardening concern.",
        "security_clean_status": "PLAUSIBLE_CONCERN",
    },
    "ABL-0004-R-1": {
        "line": 24,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": None,
        "peer_match_rationale": "Unique to Arm R.",
        "source_evidence": "login_handler.py line 24",
        "adjudication_rationale": "Alleges timing enumeration because rate limiting runs before hashing. Rate limiting must precede expensive hashing to prevent compute-exhaustion DoS; standard defensive security pattern.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0004-R-2": {
        "line": 31,
        "primary_category": "3_plausible_or_unresolved_concern",
        "peer_match_id": None,
        "peer_match_rationale": "Unique to Arm R.",
        "source_evidence": "login_handler.py line 31; NIST SP 800-63B Rev 4; OWASP Password Storage Cheat Sheet",
        "adjudication_rationale": "Valid hardening guidance. NIST SP 800-63B Rev 4 (Sec 3.1.1.2) requires salt >= 32 bits and PBKDF2 cost factor set as high as practical. OWASP Password Storage Cheat Sheet recommends PBKDF2-HMAC-SHA256 at 600,000+ iterations when FIPS-140 compliance is required. While 100,000 iterations in v1 protects against online brute-force when paired with sliding-window rate limiting, it offers lower resistance against offline GPU cracking than modern OWASP recommendations.",
        "security_clean_status": "PLAUSIBLE_CONCERN",
    },
    "ABL-0004-R-3": {
        "line": 34,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": "ABL-0004-N-2",
        "peer_match_rationale": "Counterpart to ABL-0004-N-2 on compare_digest input types.",
        "source_evidence": "login_handler.py line 34",
        "adjudication_rationale": "derived is str, stored_hash is typed str. Calling compare_digest with two strings is valid and safely returns False if they do not match.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0005-R-1": {
        "line": 19,
        "primary_category": "3_plausible_or_unresolved_concern",
        "peer_match_id": None,
        "peer_match_rationale": "Introduced in Arm R when bounded_stream.py context was provided.",
        "source_evidence": "chunk_consumer.py lines 6, 18-22; bounded_stream.py lines 29-30, 38-41",
        "adjudication_rationale": "StreamCapExceeded propagates out of process_stream_payload by design when input exceeds 500k bytes, as verified by test_process_stream_payload_exceeded_cap. Swallowing it would silently truncate data. Unused import on line 6 is a code quality issue (F401).",
        "security_clean_status": "PLAUSIBLE_CONCERN",
    },
    "ABL-0006-N-1": {
        "line": 23,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": "ABL-0006-R-1",
        "peer_match_rationale": "Both arms hallucinate that hmac.new is a non-existent API in Python 3.",
        "source_evidence": "token_signer.py line 23; Python standard library hmac module",
        "adjudication_rationale": "Hallucination. hmac.new(key, msg, digestmod) is the standard factory function in Python since Python 2/3.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0006-N-2": {
        "line": 34,
        "primary_category": "2_confirmed_correctness_or_reliability_defect",
        "peer_match_id": "ABL-0006-R-3",
        "peer_match_rationale": "Both arms identify unhandled binascii.Error on malformed base64 padding.",
        "source_evidence": "token_signer.py line 34",
        "adjudication_rationale": "Malformed base64 token length without proper padding raises unhandled binascii.Error instead of a clean domain exception (e.g. ValueError), causing an unhandled server crash.",
        "security_clean_status": "CONFIRMED_DEFECT",
    },
    "ABL-0006-N-3": {
        "line": 19,
        "primary_category": "2_confirmed_correctness_or_reliability_defect",
        "peer_match_id": "ABL-0006-R-2",
        "peer_match_rationale": "Both arms identify that key rotation invalidates all active session tokens.",
        "source_evidence": "token_signer.py lines 19, 33; key_vault.py lines 23-28",
        "adjudication_rationale": "EphemeralSigningKeyVault single-key rotation without grace period or key versioning abruptly invalidates all active sessions when key rotates, causing authentication denial of service for legitimate users.",
        "security_clean_status": "CONFIRMED_DEFECT",
    },
    "ABL-0006-N-4": {
        "line": 32,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": "ABL-0006-R-4",
        "peer_match_rationale": "Both arms flag token.split('.', 1) alleging issues if signature contains periods.",
        "source_evidence": "token_signer.py lines 23-24, 32",
        "adjudication_rationale": "Signature is generated via hexdigest() which is strictly hexadecimal characters [0-9a-f] and never contains periods; token splitting is deterministic and safe.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0006-R-1": {
        "line": 23,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": "ABL-0006-N-1",
        "peer_match_rationale": "Counterpart to ABL-0006-N-1 on hmac.new hallucination.",
        "source_evidence": "token_signer.py line 23; Python standard library hmac module",
        "adjudication_rationale": "Hallucination. Model self-debates in description and admits hmac.new is valid Python 3, yet still emits finding as High severity.",
        "security_clean_status": "FALSE_ALARM",
    },
    "ABL-0006-R-2": {
        "line": 33,
        "primary_category": "2_confirmed_correctness_or_reliability_defect",
        "peer_match_id": "ABL-0006-N-3",
        "peer_match_rationale": "Counterpart to ABL-0006-N-3 on session invalidation upon key rotation.",
        "source_evidence": "token_signer.py line 33; key_vault.py lines 23-28",
        "adjudication_rationale": "Key rotation invalidates all previously issued active tokens without grace period.",
        "security_clean_status": "CONFIRMED_DEFECT",
    },
    "ABL-0006-R-3": {
        "line": 34,
        "primary_category": "2_confirmed_correctness_or_reliability_defect",
        "peer_match_id": "ABL-0006-N-2",
        "peer_match_rationale": "Counterpart to ABL-0006-N-2 on unhandled binascii.Error.",
        "source_evidence": "token_signer.py line 34",
        "adjudication_rationale": "base64.urlsafe_b64decode raises unhandled binascii.Error on invalid base64 padding.",
        "security_clean_status": "CONFIRMED_DEFECT",
    },
    "ABL-0006-R-4": {
        "line": 32,
        "primary_category": "4_supported_false_positive",
        "peer_match_id": "ABL-0006-N-4",
        "peer_match_rationale": "Counterpart to ABL-0006-N-4 on token period split.",
        "source_evidence": "token_signer.py line 32",
        "adjudication_rationale": "hexdigest() signature never contains periods; token splitting is safe.",
        "security_clean_status": "FALSE_ALARM",
    },
}


def build_ledger() -> list[dict]:
    with open(RAW_RESULTS_PATH, encoding="utf-8") as f:
        raw_data = json.load(f)

    run_id = raw_data["metadata"]["run_id"]
    ledger_entries = []

    for slot_idx, case in enumerate(raw_data["results"]):
        fid = case["fixture_id"]
        arm_code = case["arm"]
        arm_label = f"Arm {arm_code}"
        findings = case["findings"]

        for f_idx, f in enumerate(findings):
            finding_id = f"{fid}-{arm_code}-{f_idx + 1}"
            adj = ADJUDICATION_DEFINITIONS.get(finding_id)
            if not adj:
                raise ValueError(f"Missing adjudication definition for {finding_id}")

            entry = {
                "finding_id": finding_id,
                "run_id": run_id,
                "fixture_id": fid,
                "fixture_version": "v1",
                "arm": arm_label,
                "raw_slot_index": slot_idx,
                "raw_finding_index": f_idx,
                "raw_title": f.get("title"),
                "raw_line": f.get("line") or adj["line"],
                "raw_severity": f.get("severity"),
                "raw_cwe_id": f.get("cwe_id"),
                "raw_description": f.get("description"),
                "primary_category": adj["primary_category"],
                "security_clean_status": adj["security_clean_status"],
                "peer_match_id": adj["peer_match_id"],
                "peer_match_rationale": adj["peer_match_rationale"],
                "source_evidence": adj["source_evidence"],
                "adjudication_rationale": adj["adjudication_rationale"],
            }
            ledger_entries.append(entry)

    return ledger_entries


def count_by_cat(entries: list[dict]) -> dict:
    return {
        "confirmed_security_vulnerabilities": sum(1 for e in entries if e["primary_category"] == "1_confirmed_security_vulnerability"),
        "confirmed_correctness_reliability_defects": sum(1 for e in entries if e["primary_category"] == "2_confirmed_correctness_or_reliability_defect"),
        "plausible_or_unresolved_concerns": sum(1 for e in entries if e["primary_category"] == "3_plausible_or_unresolved_concern"),
        "supported_false_positives": sum(1 for e in entries if e["primary_category"] == "4_supported_false_positive"),
        "duplicate_findings": sum(1 for e in entries if e["primary_category"] == "5_duplicate_finding"),
        "not_adjudicable": sum(1 for e in entries if e["primary_category"] == "6_not_adjudicable"),
        "total_candidate_findings": len(entries),
    }


def compute_metrics(ledger: list[dict]) -> dict:
    total_findings = len(ledger)
    arm_n = [e for e in ledger if e["arm"] == "Arm N"]
    arm_r = [e for e in ledger if e["arm"] == "Arm R"]

    # All-fixture aggregates (D=6)
    all_n = count_by_cat(arm_n)
    all_r = count_by_cat(arm_r)

    # Multi-Tier Denominator Evaluation:
    # Tier 1: Operational Remote Security-Clean Cohort (D=5: ABL-0001 to ABL-0005, excluding ABL-0006)
    # Under online remote threat model: rate limiting + 100k iterations prevents compromise
    d5_n = [e for e in arm_n if e["fixture_id"] != "ABL-0006"]
    d5_r = [e for e in arm_r if e["fixture_id"] != "ABL-0006"]
    d5_n_metrics = count_by_cat(d5_n)
    d5_r_metrics = count_by_cat(d5_r)

    # Tier 2: Comprehensive Security-Clean Cohort (D=4: ABL-0001, ABL-0002, ABL-0003, ABL-0005)
    # Excludes ABL-0006 (reliability defect) AND ABL-0004 (unverified caller-provided salt, 100k < OWASP 600k work factor, unbounded input)
    d4_n = [e for e in arm_n if e["fixture_id"] not in ["ABL-0006", "ABL-0004"]]
    d4_r = [e for e in arm_r if e["fixture_id"] not in ["ABL-0006", "ABL-0004"]]
    d4_n_metrics = count_by_cat(d4_n)
    d4_r_metrics = count_by_cat(d4_r)

    # Tier 3: Zero-Code-Smell Cohort (D=1: ABL-0003 only)
    # Excludes fixtures with any maintainability or code smell:
    # ABL-0001 (fragile startswith prefix), ABL-0002 (unused argument ARG001),
    # ABL-0004 (unverified salt contract / sub-optimal PBKDF2), ABL-0005 (unused import F401),
    # ABL-0006 (confirmed reliability defects).
    d1_n = [e for e in arm_n if e["fixture_id"] == "ABL-0003"]
    d1_r = [e for e in arm_r if e["fixture_id"] == "ABL-0003"]
    d1_n_metrics = count_by_cat(d1_n)
    d1_r_metrics = count_by_cat(d1_r)

    # Excluded cohorts
    excl_abl0006_n = [e for e in arm_n if e["fixture_id"] == "ABL-0006"]
    excl_abl0006_r = [e for e in arm_r if e["fixture_id"] == "ABL-0006"]
    excl_abl0004_n = [e for e in arm_n if e["fixture_id"] == "ABL-0004"]
    excl_abl0004_r = [e for e in arm_r if e["fixture_id"] == "ABL-0004"]

    # Per-fixture counts
    fixtures = ["ABL-0001", "ABL-0002", "ABL-0003", "ABL-0004", "ABL-0005", "ABL-0006"]
    per_fixture = {}
    for f in fixtures:
        f_n = [e for e in arm_n if e["fixture_id"] == f]
        f_r = [e for e in arm_r if e["fixture_id"] == f]
        per_fixture[f] = {
            "arm_n": {
                "total": len(f_n),
                "false_positives": sum(1 for e in f_n if e["primary_category"] == "4_supported_false_positive"),
                "defects": sum(1 for e in f_n if e["primary_category"] == "2_confirmed_correctness_or_reliability_defect"),
                "concerns": sum(1 for e in f_n if e["primary_category"] == "3_plausible_or_unresolved_concern"),
                "finding_ids": [e["finding_id"] for e in f_n],
            },
            "arm_r": {
                "total": len(f_r),
                "false_positives": sum(1 for e in f_r if e["primary_category"] == "4_supported_false_positive"),
                "defects": sum(1 for e in f_r if e["primary_category"] == "2_confirmed_correctness_or_reliability_defect"),
                "concerns": sum(1 for e in f_r if e["primary_category"] == "3_plausible_or_unresolved_concern"),
                "finding_ids": [e["finding_id"] for e in f_r],
            },
        }

    return {
        "canonical_run_id": ledger[0]["run_id"],
        "total_raw_findings": total_findings,
        "methodological_interpretation": "Tiers 1, 2, and 3 are overlapping, post-hoc exploratory sensitivity subsets derived from the same six matched fixture pairs evaluated in a single run. They reuse identical underlying model outputs and do NOT constitute independent replications or formal statistical hypothesis tests.",
        "all_fixtures_cohort": {
            "denominator": 6,
            "arm_n": all_n,
            "arm_r": all_r,
        },
        "operational_clean_cohort_d5": {
            "tier_name": "Tier 1: Operational Online-Authentication Cohort",
            "denominator": 5,
            "eligible_fixtures": ["ABL-0001", "ABL-0002", "ABL-0003", "ABL-0004", "ABL-0005"],
            "eligibility_rule": "OPERATIONAL_ONLINE_AUTH_ONLY (Narrow single-account guessing defense; excludes distributed credential stuffing, offline cracking, and unbounded payload memory exhaustion; ABL-0004-v1 conditionally retained under narrow scope only)",
            "arm_n": d5_n_metrics,
            "arm_r": d5_r_metrics,
            "delta_r_minus_n": {
                "false_positives": d5_r_metrics["supported_false_positives"] - d5_n_metrics["supported_false_positives"],
                "total_findings": d5_r_metrics["total_candidate_findings"] - d5_n_metrics["total_candidate_findings"],
            },
        },
        "comprehensive_security_clean_cohort_d4": {
            "tier_name": "Tier 2: Comprehensive Security-Clean Cohort",
            "denominator": 4,
            "eligible_fixtures": ["ABL-0001", "ABL-0002", "ABL-0003", "ABL-0005"],
            "eligibility_rule": "COMPREHENSIVE_SECURITY_CLEAN (Self-contained defensive hygiene; excludes ABL-0006 reliability defects and ABL-0004 unverified caller salt, 100k < 600k OWASP work factor, and unvalidated input length)",
            "arm_n": d4_n_metrics,
            "arm_r": d4_r_metrics,
            "delta_r_minus_n": {
                "false_positives": d4_r_metrics["supported_false_positives"] - d4_n_metrics["supported_false_positives"],
                "total_findings": d4_r_metrics["total_candidate_findings"] - d4_n_metrics["total_candidate_findings"],
            },
        },
        "strict_clean_cohort_d4": {
            "tier_name": "Tier 2: Comprehensive Security-Clean Cohort",
            "denominator": 4,
            "eligible_fixtures": ["ABL-0001", "ABL-0002", "ABL-0003", "ABL-0005"],
            "eligibility_rule": "COMPREHENSIVE_SECURITY_CLEAN (Self-contained defensive hygiene; excludes ABL-0006 reliability defects and ABL-0004 unverified caller salt, 100k < 600k OWASP work factor, and unvalidated input length)",
            "arm_n": d4_n_metrics,
            "arm_r": d4_r_metrics,
            "delta_r_minus_n": {
                "false_positives": d4_r_metrics["supported_false_positives"] - d4_n_metrics["supported_false_positives"],
                "total_findings": d4_r_metrics["total_candidate_findings"] - d4_n_metrics["total_candidate_findings"],
            },
        },
        "zero_code_smell_cohort_d1": {
            "tier_name": "Tier 3: Lint-Clean / Zero-Code-Smell Cohort",
            "denominator": 1,
            "eligible_fixtures": ["ABL-0003"],
            "eligibility_rule": "LINT_CLEAN_ZERO_CODE_SMELL (Zero linter/maintainability smells; single matched illustrative case ABL-0003; excludes ABL-0001 prefix-check, ABL-0002 unused param, ABL-0004 unverified salt/100k, ABL-0005 unused import, ABL-0006 reliability defects)",
            "arm_n": d1_n_metrics,
            "arm_r": d1_r_metrics,
            "delta_r_minus_n": {
                "false_positives": d1_r_metrics["supported_false_positives"] - d1_n_metrics["supported_false_positives"],
                "total_findings": d1_r_metrics["total_candidate_findings"] - d1_n_metrics["total_candidate_findings"],
            },
        },
        "excluded_cohort_abl0006": {
            "denominator": 1,
            "fixture": "ABL-0006",
            "exclusion_rationale": "MIXED_OR_DEFECTIVE: Confirmed unhandled decode exception (binascii.Error) and session invalidation upon single-key rotation.",
            "arm_n": count_by_cat(excl_abl0006_n),
            "arm_r": count_by_cat(excl_abl0006_r),
            "excluded_finding_ids": {
                "arm_n": [e["finding_id"] for e in excl_abl0006_n],
                "arm_r": [e["finding_id"] for e in excl_abl0006_r],
            },
        },
        "excluded_cohort_abl0004": {
            "denominator": 1,
            "fixture": "ABL-0004",
            "exclusion_rationale": "UNRESOLVED_SECURITY_CONCERN: Caller-provided salt without generation or validation, hardcoded 100k iterations below OWASP recommendation (600k), and unvalidated input length.",
            "arm_n": count_by_cat(excl_abl0004_n),
            "arm_r": count_by_cat(excl_abl0004_r),
            "excluded_finding_ids": {
                "arm_n": [e["finding_id"] for e in excl_abl0004_n],
                "arm_r": [e["finding_id"] for e in excl_abl0004_r],
            },
        },
        "per_fixture_breakdown": per_fixture,
    }


def main():
    ledger = build_ledger()
    assert len(ledger) == 27, f"Expected 27 findings, got {len(ledger)}"

    # Save JSON ledger
    LEDGER_JSON_PATH.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
    print(f"Saved canonical ledger JSON: {LEDGER_JSON_PATH}")

    # Save CSV ledger
    fieldnames = list(ledger[0].keys())
    with open(LEDGER_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ledger)
    print(f"Saved canonical ledger CSV: {LEDGER_CSV_PATH}")

    # Save summary metrics
    summary = compute_metrics(ledger)
    SUMMARY_JSON_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Saved summary metrics JSON: {SUMMARY_JSON_PATH}")


if __name__ == "__main__":
    main()
