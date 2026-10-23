"""Synchronize benchmark manifest provenance and fixture paths for all 100 cases.

Ensures:
1. 18 upstream repository snapshots in data/fixtures/upstream_snapshots/ are linked via fixture_path.
2. synthetic=False and source_type="upstream_repository_snapshot" for those 18 cases.
3. synthetic=True and source_type="synthetic_fixture" for the 32 synthetic buggy cases.
4. synthetic=True and source_type="handcrafted_clean_fixture" for CTRL-0001..CTRL-0018.
5. synthetic=True and source_type="synthetic_fixture" for CTRL-0019..CTRL-0050.
"""

from __future__ import annotations

import json
from pathlib import Path

from auditor.evaluation.manifest import load_benchmark_manifest
from auditor.evaluation.runner import EvaluationRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "data" / "benchmark_manifest.json"

HIST_BUGGY_IDS = {1, 2, 6, 7, 8, 9, 14, 15, 17, 19, 20, 21, 25, 26, 27, 31, 32, 33}


def main() -> None:
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        data = json.load(f)

    cases = data.get("cases", [])
    for c in cases:
        cid = c["case_id"]
        is_buggy = c.get("is_buggy", True)
        num = int(cid.split("-")[1])

        if is_buggy:
            if num in HIST_BUGGY_IDS:
                target_file = c["target_file"]
                c["synthetic"] = False
                c["source_type"] = "upstream_repository_snapshot"
                c["fixture_path"] = f"data/fixtures/upstream_snapshots/{cid}/{target_file}"
                prov = c.get("provenance") or {}
                prov["source_type"] = "upstream_repository_snapshot"
                prov["synthetic"] = False
                c["provenance"] = prov
            else:
                c["synthetic"] = True
                c["source_type"] = "synthetic_fixture"
                prov = c.get("provenance") or {}
                prov["source_type"] = "synthetic_fixture"
                prov["synthetic"] = True
                c["provenance"] = prov
        else:
            c["synthetic"] = True
            if num <= 18:
                c["source_type"] = "handcrafted_clean_fixture"
                prov = c.get("provenance") or {}
                prov["source_type"] = "handcrafted_clean_fixture"
                prov["synthetic"] = True
                c["provenance"] = prov
            else:
                c["source_type"] = "synthetic_fixture"
                prov = c.get("provenance") or {}
                prov["source_type"] = "synthetic_fixture"
                prov["synthetic"] = True
                c["provenance"] = prov

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Validate with Pydantic manifest loader
    manifest = load_benchmark_manifest(MANIFEST_PATH)
    print(f"Manifest schema valid! Total cases: {len(manifest.cases)}")

    # Verify that all 100 cases resolve authentic code on disk without placeholders
    runner = EvaluationRunner(manifest=manifest)
    resolved_count = 0
    for mc in manifest.cases:
        code = runner._resolve_case_code(mc, allow_placeholder=False)
        assert len(code) > 0, f"Empty code for {mc.case_id}"
        resolved_count += 1

    print(f"ALL {resolved_count}/100 cases resolve to authentic code on disk without placeholders!")


if __name__ == "__main__":
    main()
