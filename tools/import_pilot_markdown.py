"""Development utility to extract structured pilot cases from Markdown into canonical JSON.

Usage:
    uv run python tools/import_pilot_markdown.py
"""

import json
import re
from pathlib import Path


def parse_ground_truth_locus(locus_raw: str | None) -> list[list[int]]:
    """Parse ground-truth defect line ranges from explicit, labeled locus declarations.

    Rules:
    - Strips parenthetical narrative notes (e.g. '(specifically line 393: ...)', '(in func)')
      to avoid parsing incidental line number mentions as separate defects.
    - Preserves multiple distinct disjoint loci (e.g. 'Line 250 (...) and Lines 292–293 (...)').
    - Disallows duplicate or subsumed loci: single lines or spans falling within an already
      recorded locus range are not added as separate defects.
    """
    if not locus_raw:
        return []

    # 1. Strip parenthetical comments and explanatory text
    cleaned_locus = re.sub(r"\(.*?\)", "", locus_raw)

    # 2. Extract explicit 'Line(s) X-Y' or 'Line X' patterns
    matches = re.findall(r"(?:Lines?|line)\s*(\d+)(?:[–\-](\d+))?", cleaned_locus)
    extracted: list[list[int]] = []
    for s, e in matches:
        start_l = int(s)
        end_l = int(e) if e else start_l
        if start_l > end_l:
            start_l, end_l = end_l, start_l
        extracted.append([start_l, end_l])

    # Fallback if no 'Line' prefix matched but raw span digits exist (e.g. table cells)
    if not extracted:
        parts = re.split(r"[,;]|\band\b", cleaned_locus)
        for part in parts:
            part = part.strip()
            m = re.search(r"(\d+)(?:[–\-](\d+))?", part)
            if m:
                s, e = m.groups()
                start_l = int(s)
                end_l = int(e) if e else start_l
                if start_l > end_l:
                    start_l, end_l = end_l, start_l
                extracted.append([start_l, end_l])

    # 3. Apply subsumption and containment filter
    line_ranges: list[list[int]] = []
    for r in extracted:
        # Check if r is already contained within an existing range
        is_subsumed = False
        for ex in line_ranges:
            if ex[0] <= r[0] and r[1] <= ex[1]:
                is_subsumed = True
                break
        if is_subsumed:
            continue

        # Check if r subsumes any previously added narrower range
        line_ranges = [ex for ex in line_ranges if not (r[0] <= ex[0] and ex[1] <= r[1])]
        line_ranges.append(r)

    return line_ranges


def parse_pilot_markdown(markdown_path: Path) -> list[dict]:
    content = markdown_path.read_text(encoding="utf-8")
    sections = re.split(r"\n### (CAND-\d+):", content)

    cases = []
    for i in range(1, len(sections), 2):
        cand_id = sections[i]
        block = sections[i + 1].split("\n---")[0]

        def get_field(pattern: str, text: str = block) -> str | None:
            m = re.search(pattern, text)
            if m:
                val = m.group(1)
                return val.strip() if val else None
            return None

        cat_raw = get_field(r"\- \*\*Category\*\*:\s*Category (\d+)")
        impact_raw = get_field(r"\- \*\*Impact Attribute\*\*:\s*`?([a-zA-Z0-9_]+)`?")
        repo_raw = get_field(r"\- \*\*Repository\*\*:\s*`([^`]+)`")
        buggy_sha = get_field(r"\- \*\*Buggy Commit SHA\*\*:\s*`([a-f0-9]+)`")
        fixed_sha = get_field(r"\- \*\*Fixed Commit SHA\*\*:\s*`([a-f0-9]+)`")
        file_path_raw = get_field(r"\- \*\*Affected File Path\*\*:\s*`([^`]+)`")
        locus_raw = get_field(r"\- \*\*Ground-Truth Pre-Fix Locus\*\*:\s*(.+)")
        primary_cwe = get_field(r"\- \*\*Primary CWE\*\*:\s*(CWE-\d+)")
        alt_cwes_raw = get_field(r"\- \*\*Acceptable Alternative CWE Set\*\*:\s*(`?\[[^\]]+\]`?)")
        reproducer = get_field(r"\- \*\*Reproducer / Test\*\*:\s*(.+)")
        quality = get_field(r"\- \*\*Evidence Quality Level\*\*:\s*(Level [ABC])")
        status = get_field(r"\- \*\*Final Status\*\*:\s*`?([A-Z_]+)`?")
        advisory = get_field(r"\- \*\*Advisory / CVE\*\*:\s*(.+)")

        category_id = int(cat_raw) if cat_raw else None

        alt_cwes: list[str] = []
        if alt_cwes_raw:
            cleaned_json = alt_cwes_raw.replace("`", "")
            try:
                alt_cwes = sorted(list(set(json.loads(cleaned_json))))
            except json.JSONDecodeError:
                alt_cwes = []

        line_ranges = parse_ground_truth_locus(locus_raw)

        defects = []
        target_file = file_path_raw.split(" ")[0] if file_path_raw else ""
        for idx, (s, e) in enumerate(line_ranges):
            defects.append(
                {
                    "defect_id": f"{cand_id}-DEF-{idx + 1}",
                    "category_id": category_id,
                    "impact": impact_raw,
                    "primary_cwe": primary_cwe,
                    "acceptable_alternative_cwes": alt_cwes,
                    "file_path": target_file,
                    "start_line": s,
                    "end_line": e,
                    "description": f"Ground-truth locus {s}-{e}",
                }
            )

        cases.append(
            {
                "case_id": cand_id,
                "candidate_id": cand_id,
                "verification_status": status or "GROUND_TRUTH_VERIFIED",
                "quality_level": quality or "Level A",
                "repository": repo_raw,
                "commit_hash": buggy_sha,
                "buggy_commit": buggy_sha,
                "fixed_commit": fixed_sha,
                "is_buggy": True,
                "category_id": category_id,
                "impact": impact_raw,
                "primary_cwe": primary_cwe,
                "acceptable_alternative_cwes": alt_cwes,
                "target_file": target_file,
                "line_ranges": line_ranges,
                "defects": defects,
                "reproducer": reproducer,
                "provenance": {
                    "advisory": advisory,
                    "source_doc": "Project Documents/dataset/ground_truth_validation_pilot.md",
                },
            }
        )
    return cases


def main():
    repo_root = Path(__file__).resolve().parent.parent
    markdown_path = repo_root / "Project Documents" / "dataset" / "ground_truth_validation_pilot.md"
    out_dir = repo_root / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "pilot_cases.json"

    cases = parse_pilot_markdown(markdown_path)
    payload = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "description": "Ground-truth verified pilot cases (12 cases) for AI Code Auditor benchmark evaluation.",
        "case_count": len(cases),
        "cases": cases,
    }

    formatted_json = json.dumps(payload, indent=2) + "\n"
    out_path.write_text(formatted_json, encoding="utf-8")
    print(f"Exported {len(cases)} pilot cases to canonical path: {out_path}")


if __name__ == "__main__":
    main()
