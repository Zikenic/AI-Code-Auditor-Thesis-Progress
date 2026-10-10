#!/usr/bin/env python3
"""Pilot Upstream Audit: Primary Source Verification of Pilot Ground-Truth Cases.

Audits all 12 pilot benchmark cases plus reserve candidate CAND-0036 directly against
authentic upstream Git repositories. Verifies:
1. Commit existence for both buggy (pre-fix) and fixed revisions.
2. File existence and content extraction at the exact buggy commit.
3. 1-indexed pre-fix locus line coordinates and line text matching Table 1.
4. Behavioral code anchors for the defect in the buggy state.
5. Behavioral code anchors for the fix in the fixed state.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = Path(__file__).resolve().parent
SCRATCH_REPOS_DIR = REPO_ROOT / "scratch" / "upstream_repos" / "pilot_audit"


@dataclass
class UpstreamCaseSpec:
    candidate_id: str
    category: str
    repo_slug: str  # owner/repo
    folder_name: str
    buggy_commit: str
    fixed_commit: str
    affected_file: str
    loci: list[tuple[int, int]]  # [(start, end), ...]
    buggy_anchors: list[str]
    fixed_anchors: list[str]
    cwe_primary: str
    cwe_alternatives: list[str]
    advisory_or_cve: str
    notes: str


PILOT_SPECS: list[UpstreamCaseSpec] = [
    UpstreamCaseSpec(
        candidate_id="CAND-0001",
        category="Category 1 — Boundary / Conditional / Logic",
        repo_slug="tornadoweb/tornado",
        folder_name="tornadoweb_tornado",
        buggy_commit="2ca8821d006f6693f920a4b183a3a7c985a5c8ad",
        fixed_commit="4f486a4aec746e9d66441600ee3b0743228b061c",
        affected_file="tornado/http1connection.py",
        loci=[(390, 394)],
        buggy_anchors=['and "Transfer-Encoding" not in headers'],
        fixed_anchors=['headers["Transfer-Encoding"] == "chunked"'],
        cwe_primary="CWE-670",
        cwe_alternatives=["CWE-440", "CWE-20"],
        advisory_or_cve="N/A (Functional logic flaw)",
        notes="Logic error in write_headers suppressed chunking when Transfer-Encoding explicitly present.",
    ),
    UpstreamCaseSpec(
        candidate_id="CAND-0002",
        category="Category 1 — Boundary / Conditional / Logic",
        repo_slug="tiangolo/fastapi",
        folder_name="tiangolo_fastapi",
        buggy_commit="210af1fd3dc0f612a08fa02a0cb3f5adb81e5bfb",
        fixed_commit="02441ff0313d5b471b662293244c53e712f1243f",
        affected_file="fastapi/routing.py",
        loci=[(498, 502)],
        buggy_anchors=["route = APIWebSocketRoute(path, endpoint=endpoint, name=name)"],
        fixed_anchors=["dependency_overrides_provider=self.dependency_overrides_provider"],
        cwe_primary="CWE-670",
        cwe_alternatives=["CWE-440"],
        advisory_or_cve="N/A (Functional logic flaw)",
        notes="add_api_websocket_route failed to propagate dependency_overrides_provider.",
    ),
    UpstreamCaseSpec(
        candidate_id="CAND-0007",
        category="Category 2 — Input Validation / Sanitization",
        repo_slug="tiangolo/fastapi",
        folder_name="tiangolo_fastapi",
        buggy_commit="90120dd6e83d997fa2f7f54119a2e0cf906b1ded",
        fixed_commit="fa7e3c996edf2d5482fff8f9d890ac2390dede4d",
        affected_file="fastapi/routing.py",
        loci=[(182, 184)],
        buggy_anchors=["body_bytes = await request.body()", "body = await request.json()"],
        fixed_anchors=[
            'content_type_value = request.headers.get("content-type")',
            'message.get_content_maintype() == "application"',
        ],
        cwe_primary="CWE-352",
        cwe_alternatives=["CWE-20", "CWE-345"],
        advisory_or_cve="GHSA-8h2j-cgx8-6xv7 / CVE-2021-32677",
        notes="FastAPI parsed JSON bodies without checking Content-Type header, enabling simple-request CSRF.",
    ),
    UpstreamCaseSpec(
        candidate_id="CAND-0009",
        category="Category 2 — Input Validation / Sanitization",
        repo_slug="pallets/jinja",
        folder_name="pallets_jinja",
        buggy_commit="a7863ba9d3521f1450f821119c50d19d7ecea329",
        fixed_commit="0668239dc6b44ef38e7a6c9f91f312fd4ca581cb",
        affected_file="src/jinja2/filters.py",
        loci=[(250, 250), (292, 293)],
        buggy_anchors=["yield from value.items()", "if _space_re.search(key) is not None:"],
        fixed_anchors=[
            '_attr_key_re = re.compile(r"[\\s/>=]", flags=re.ASCII)',
            "if _attr_key_re.search(key) is not None:",
        ],
        cwe_primary="CWE-79",
        cwe_alternatives=["CWE-20", "CWE-116"],
        advisory_or_cve="GHSA-h75v-3vvj-5mfj / CVE-2024-34064",
        notes="xmlattr filter permitted '/', '>', '=' in attribute keys, allowing quote breakout and attribute injection.",
    ),
    UpstreamCaseSpec(
        candidate_id="CAND-0014",
        category="Category 3 — SQL / ORM Injection",
        repo_slug="django/django",
        folder_name="django_django",
        buggy_commit="425718726b7d2edd7b8a043f8976e437262b5098",
        fixed_commit="54eb8a374d5d98594b264e8ec22337819b37443c",
        affected_file="django/db/models/functions/datetime.py",
        loci=[(45, 51), (225, 236)],
        buggy_anchors=[
            "self.lookup_name = lookup_name",
            "super().__init__(expression, output_field=output_field, **extra)",
        ],
        fixed_anchors=[
            "extract_trunc_lookup_pattern",
            'raise ValueError("Invalid lookup_name: %s" % self.lookup_name)',
        ],
        cwe_primary="CWE-89",
        cwe_alternatives=["CWE-20", "CWE-943"],
        advisory_or_cve="GHSA-p64x-8rxx-wf6q / CVE-2022-34265",
        notes="Unsanitized lookup_name and kind in Trunc/Extract allowed SQL injection via crafted date part names.",
    ),
    UpstreamCaseSpec(
        candidate_id="CAND-0017",
        category="Category 3 — SQL / ORM Injection",
        repo_slug="tortoise/tortoise-orm",
        folder_name="tortoise_tortoise-orm",
        buggy_commit="816ff00e988f79b4ff1601f247062bb5eb9db802",
        fixed_commit="91c364053e0ddf77edc5442914c6f049512678b3",
        affected_file="tortoise/backends/mysql/executor.py",
        loci=[(19, 45)],
        buggy_anchors=['functions.Cast(field, SqlTypes.CHAR).like(f"%{value}%")'],
        fixed_anchors=["escape_like", "StrWrapper"],
        cwe_primary="CWE-89",
        cwe_alternatives=["CWE-943", "CWE-20"],
        advisory_or_cve="GHSA-9j2c-x8qm-qmjq / CVE-2020-11010",
        notes="MySQL filter functions formatted user input directly into LIKE clauses without wildcard or delimiter escaping.",
    ),
    UpstreamCaseSpec(
        candidate_id="CAND-0019",
        category="Category 4 — Path Traversal / Unsafe File Operations",
        repo_slug="aio-libs/aiohttp",
        folder_name="aio-libs_aiohttp",
        buggy_commit="33ccdfb0a12690af5bb49bda2319ec0907fa7827",
        fixed_commit="1c335944d6a8b1298baf179b7c0b3069f10c514b",
        affected_file="aiohttp/web_urldispatcher.py",
        loci=[(574, 576), (643, 645)],
        buggy_anchors=["if not self._follow_symlinks:", "filepath.relative_to(self._directory)"],
        fixed_anchors=[
            "normalized_path = Path(os.path.normpath(unresolved_path))",
            "normalized_path.relative_to(self._directory)",
        ],
        cwe_primary="CWE-22",
        cwe_alternatives=["CWE-59", "CWE-20"],
        advisory_or_cve="GHSA-5h86-8mv2-jq9f / CVE-2024-23334",
        notes="Path boundary check was gated behind 'if not self._follow_symlinks', allowing directory escape when symlinks enabled.",
    ),
    UpstreamCaseSpec(
        candidate_id="CAND-0021",
        category="Category 4 — Path Traversal / Unsafe File Operations",
        repo_slug="encode/starlette",
        folder_name="encode_starlette",
        buggy_commit="24c1fac62a80bb153c6548145334fc643991e35a",
        fixed_commit="1797de464124b090f10cf570441e8292936d63e3",
        affected_file="starlette/staticfiles.py",
        loci=[(172, 172)],
        buggy_anchors=["if os.path.commonprefix([full_path, directory]) != directory:"],
        fixed_anchors=["if os.path.commonpath([full_path, directory]) != directory:"],
        cwe_primary="CWE-22",
        cwe_alternatives=["CWE-20"],
        advisory_or_cve="GHSA-v5gw-mw7f-84px / CVE-2023-29159",
        notes="commonprefix operates on string characters rather than path segments, allowing sibling directory escape.",
    ),
    UpstreamCaseSpec(
        candidate_id="CAND-0025",
        category="Category 5 — Authentication",
        repo_slug="jpadilla/pyjwt",
        folder_name="jpadilla_pyjwt",
        buggy_commit="24b29adfebcb4f057a3cef5aaf35653bc0c1c8cc",
        fixed_commit="9c528670c455b8d948aff95ed50e22940d1ad3fc",
        affected_file="jwt/algorithms.py",
        loci=[(186, 197)],
        buggy_anchors=['b"ssh-rsa"'],
        fixed_anchors=["is_pem_format(key) or is_ssh_key(key)", "InvalidKeyError"],
        cwe_primary="CWE-347",
        cwe_alternatives=["CWE-287", "CWE-327"],
        advisory_or_cve="GHSA-ffqj-6fqr-9h24 / CVE-2022-29217",
        notes="Incomplete blacklist of asymmetric key headers allowed OpenSSH Ed25519 and ECDSA public keys to be parsed as HMAC secrets.",
    ),
    UpstreamCaseSpec(
        candidate_id="CAND-0027",
        category="Category 5 — Authentication",
        repo_slug="lepture/authlib",
        folder_name="lepture_authlib",
        buggy_commit="bb7a315befbad333faf9a23ef574d6e3134a6774",
        fixed_commit="b87c32ed07b8ae7f805873e1c9cafd1016761df7",
        affected_file="authlib/jose/__init__.py",
        loci=[(49, 49)],
        buggy_anchors=["jwt = JsonWebToken(list(JsonWebSignature.ALGORITHMS_REGISTRY.keys()))"],
        fixed_anchors=['"HS256"', "jwt = JsonWebToken("],
        cwe_primary="CWE-347",
        cwe_alternatives=["CWE-287", "CWE-327"],
        advisory_or_cve="GHSA-7wc2-qxgw-g8gg / CVE-2026-28802",
        notes="Default JsonWebToken singleton initialized with all registry algorithms including insecure 'none'.",
    ),
    UpstreamCaseSpec(
        candidate_id="CAND-0031",
        category="Category 6 — Authorization",
        repo_slug="jupyterhub/jupyterhub",
        folder_name="jupyterhub_jupyterhub",
        buggy_commit="b4053616743eb011e5bb568700f25afca17aef53",
        fixed_commit="99e2720b0fc626cbeeca3c6337f917fdacfaa428",
        affected_file="jupyterhub/apihandlers/users.py",
        loci=[(265, 267), (328, 331)],
        buggy_anchors=["user.admin = data['admin']"],
        fixed_anchors=[
            "if not self.current_user.admin:",
            'raise web.HTTPError(403, "Only admins can grant admin permissions")',
        ],
        cwe_primary="CWE-269",
        cwe_alternatives=["CWE-863", "CWE-285"],
        advisory_or_cve="GHSA-9x4q-3gxw-849f / CVE-2024-41942",
        notes="admin:users scoped user could grant admin=True without requiring caller to possess admin status.",
    ),
    UpstreamCaseSpec(
        candidate_id="CAND-0032",
        category="Category 6 — Authorization",
        repo_slug="zulip/zulip",
        folder_name="zulip_zulip",
        buggy_commit="ea0b8cc01133c79033868efee3edc6c1e3fa0f2b",
        fixed_commit="a30cd12433e3a9f7764763ba38849ac635da5283",
        affected_file="zerver/lib/message.py",
        loci=[(825, 827), (842, 856)],
        buggy_anchors=["if has_user_message:\n        return True", "return Subscription.objects.filter("],
        fixed_anchors=["def is_subscribed_helper() -> bool:", "return has_user_message and is_subscribed_helper()"],
        cwe_primary="CWE-863",
        cwe_alternatives=["CWE-285", "CWE-639"],
        advisory_or_cve="GHSA-q3wg-jm9p-35fj / CVE-2023-32678",
        notes="has_message_access granted access to any user with a user_message row, enabling unsubscribed private stream edits.",
    ),
    UpstreamCaseSpec(
        candidate_id="CAND-0036",
        category="Category 2 — Input Validation / Sanitization (Reserve)",
        repo_slug="django/django",
        folder_name="django_django",
        buggy_commit="1f2dd37f6fcefdd10ed44cb233b2e62b520afb38",
        fixed_commit="84b2da5552e100ae3294f564f6c862fef8d0e693",
        affected_file="django/core/cache/backends/memcached.py",
        loci=[(65, 86)],
        buggy_anchors=[
            "def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):",
            "def get(self, key, default=None, version=None):",
        ],
        fixed_anchors=["self.validate_key(key)", "def validate_key(self, key):", "InvalidCacheKey"],
        cwe_primary="CWE-20",
        cwe_alternatives=["CWE-116", "CWE-200"],
        advisory_or_cve="GHSA-wpjr-j57x-wxfw / CVE-2020-13254",
        notes="Omission of validate_key(key) allowed control characters and whitespace in Memcached keys causing cache poisoning/collision.",
    ),
]


def ensure_repo(spec: UpstreamCaseSpec, base_dir: Path) -> Path:
    """Ensure authentic git repo exists and contains the required commits."""
    repo_dir = base_dir / spec.folder_name
    if not repo_dir.exists():
        repo_dir.mkdir(parents=True, exist_ok=True)
        url = f"https://github.com/{spec.repo_slug}.git"
        print(f"Cloning {url} into {repo_dir}...")
        subprocess.run(["git", "clone", "--bare", url, str(repo_dir)], check=True)

    # Verify buggy commit
    res_b = subprocess.run(
        ["git", "-C", str(repo_dir), "cat-file", "-e", spec.buggy_commit],
        capture_output=True,
    )
    if res_b.returncode != 0:
        print(f"Fetching commit {spec.buggy_commit} in {repo_dir}...")
        subprocess.run(
            ["git", "-C", str(repo_dir), "fetch", "origin", spec.buggy_commit],
            check=True,
        )

    # Verify fixed commit
    res_f = subprocess.run(
        ["git", "-C", str(repo_dir), "cat-file", "-e", spec.fixed_commit],
        capture_output=True,
    )
    if res_f.returncode != 0:
        print(f"Fetching commit {spec.fixed_commit} in {repo_dir}...")
        subprocess.run(
            ["git", "-C", str(repo_dir), "fetch", "origin", spec.fixed_commit],
            check=True,
        )

    return repo_dir


def extract_file_at_commit(repo_dir: Path, commit_sha: str, file_path: str) -> str:
    """Extract raw file contents at specific commit."""
    cmd = ["git", "-C", str(repo_dir), "show", f"{commit_sha}:{file_path}"]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    return res.stdout


def audit_case(spec: UpstreamCaseSpec, base_dir: Path) -> dict[str, Any]:
    """Execute complete upstream audit for a single benchmark candidate."""
    repo_dir = ensure_repo(spec, base_dir)

    # 1. Inspect buggy state
    buggy_content = extract_file_at_commit(repo_dir, spec.buggy_commit, spec.affected_file)
    buggy_lines = buggy_content.splitlines()

    # 2. Inspect fixed state
    fixed_content = extract_file_at_commit(repo_dir, spec.fixed_commit, spec.affected_file)

    # 3. Check commit metadata
    commit_info_cmd = [
        "git",
        "-C",
        str(repo_dir),
        "show",
        "-s",
        "--format=%h|%an|%ad|%s",
        "--date=short",
        spec.fixed_commit,
    ]
    info_out = subprocess.run(
        commit_info_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True
    ).stdout.strip()
    fixed_short, fixed_author, fixed_date, fixed_subject = info_out.split("|", 3)

    # 4. Verify pre-fix loci
    extracted_loci_snippets: list[dict[str, Any]] = []
    loci_all_found = True
    for start, end in spec.loci:
        # 1-indexed conversion
        if 1 <= start <= len(buggy_lines) and 1 <= end <= len(buggy_lines) and start <= end:
            snippet_lines = buggy_lines[start - 1 : end]
            snippet_text = "\n".join(snippet_lines)
            extracted_loci_snippets.append(
                {
                    "range": [start, end],
                    "line_count": len(snippet_lines),
                    "snippet": snippet_text,
                }
            )
        else:
            loci_all_found = False
            extracted_loci_snippets.append(
                {
                    "range": [start, end],
                    "error": f"Locus [{start}, {end}] out of range (file has {len(buggy_lines)} lines)",
                }
            )

    # 5. Check buggy behavioral anchors strictly within declared loci
    combined_locus_snippets = "\n".join(s["snippet"] for s in extracted_loci_snippets if "snippet" in s)
    buggy_anchor_matches: list[dict[str, Any]] = []
    buggy_anchors_verified = True
    for anchor in spec.buggy_anchors:
        found_in_locus = anchor in combined_locus_snippets
        found_in_file = anchor in buggy_content
        buggy_anchor_matches.append(
            {
                "anchor": anchor,
                "present_in_locus": found_in_locus,
                "present_in_file": found_in_file,
            }
        )
        if not found_in_locus:
            buggy_anchors_verified = False

    # 6. Check fixed behavioral anchors
    fixed_anchor_matches: list[dict[str, Any]] = []
    fixed_anchors_verified = True
    for anchor in spec.fixed_anchors:
        found = anchor in fixed_content
        fixed_anchor_matches.append({"anchor": anchor, "present_in_fixed": found})
        if not found:
            fixed_anchors_verified = False

    # 7. Independent validation of genuine distinction (specifically CAND-0007 and CAND-0017)
    distinction_verified = True
    distinction_details: dict[str, Any] = {}
    if spec.candidate_id == "CAND-0007":
        # Vulnerable state has unguarded body assignment; fixed state has Content-Type check and json_body
        unguarded_in_fixed = bool(re.search(r"^\s*body = await request\.json\(\)", fixed_content, re.MULTILINE))
        content_type_in_buggy = "content-type" in buggy_content
        content_type_in_fixed = 'content_type_value = request.headers.get("content-type")' in fixed_content
        distinction_verified = (not unguarded_in_fixed) and (not content_type_in_buggy) and content_type_in_fixed
        distinction_details = {
            "unguarded_assignment_absent_in_fixed": not unguarded_in_fixed,
            "content_type_absent_in_buggy": not content_type_in_buggy,
            "content_type_present_in_fixed": content_type_in_fixed,
            "notes": "Verified that unvalidated JSON parsing is abolished in fixed revision and guarded by Content-Type header inspection.",
        }
    elif spec.candidate_id == "CAND-0017":
        # Vulnerable state has raw LIKE interpolation; fixed state uses StrWrapper and escape_like
        raw_like_in_fixed = 'functions.Cast(field, SqlTypes.CHAR).like(f"%{value}%")' in fixed_content
        escape_in_buggy = "escape_like" in buggy_content
        escape_in_fixed = "escape_like" in fixed_content
        distinction_verified = (not raw_like_in_fixed) and (not escape_in_buggy) and escape_in_fixed
        distinction_details = {
            "raw_like_absent_in_fixed": not raw_like_in_fixed,
            "escape_like_absent_in_buggy": not escape_in_buggy,
            "escape_like_present_in_fixed": escape_in_fixed,
            "notes": "Verified that unescaped LIKE interpolation is eliminated in fixed revision and replaced by escape_like sanitizer.",
        }

    status_pass = loci_all_found and buggy_anchors_verified and fixed_anchors_verified and distinction_verified

    return {
        "candidate_id": spec.candidate_id,
        "category": spec.category,
        "repo_slug": spec.repo_slug,
        "affected_file": spec.affected_file,
        "buggy_commit": spec.buggy_commit,
        "fixed_commit": spec.fixed_commit,
        "fixed_commit_meta": {
            "short_sha": fixed_short,
            "author": fixed_author,
            "date": fixed_date,
            "subject": fixed_subject,
        },
        "cwe_primary": spec.cwe_primary,
        "cwe_alternatives": spec.cwe_alternatives,
        "advisory_or_cve": spec.advisory_or_cve,
        "audit_pass": status_pass,
        "loci_verified": loci_all_found,
        "buggy_anchors_verified": buggy_anchors_verified,
        "fixed_anchors_verified": fixed_anchors_verified,
        "distinction_verified": distinction_verified,
        "distinction_details": distinction_details,
        "extracted_loci": extracted_loci_snippets,
        "buggy_anchor_results": buggy_anchor_matches,
        "fixed_anchor_results": fixed_anchor_matches,
        "notes": spec.notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit pilot ground-truth cases against authentic upstream Git")
    parser.add_argument("--scratch-dir", type=Path, default=SCRATCH_REPOS_DIR)
    parser.add_argument("--output-json", type=Path, default=EVIDENCE_DIR / "audit_results.json")
    args = parser.parse_args()

    args.scratch_dir.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 76)
    print("PHASE 2 PILOT UPSTREAM GIT AUDIT (12 PILOT CASES + CAND-0036 RESERVE)")
    print(f"Scratch Repos Directory: {args.scratch_dir}")
    print(f"Output Evidence File:    {args.output_json}")
    print("=" * 76)

    audit_records = []
    failures = 0

    for spec in PILOT_SPECS:
        print(f"\nAuditing {spec.candidate_id} ({spec.repo_slug})...")
        record = audit_case(spec, args.scratch_dir)
        audit_records.append(record)
        if record["audit_pass"]:
            print(f"  [PASS] {spec.candidate_id}: Loci & code anchors verified 100%.")
        else:
            print(f"  [FAIL] {spec.candidate_id}: Audit discrepancies detected!")
            failures += 1

    summary = {
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_cases_audited": len(PILOT_SPECS),
        "total_passed": len(PILOT_SPECS) - failures,
        "total_failed": failures,
        "all_passed": failures == 0,
        "cases": audit_records,
    }

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 76)
    print(f"Audit Complete: {len(PILOT_SPECS) - failures}/{len(PILOT_SPECS)} cases verified.")
    print(f"Results written to: {args.output_json}")
    print("=" * 76)

    if failures > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
