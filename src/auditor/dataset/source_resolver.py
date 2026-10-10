"""Helper to extract authentic target source content for pilot benchmark cases."""

from __future__ import annotations

import subprocess
from pathlib import Path

from auditor.models.ground_truth import BenchmarkCase

REPO_ROOT = Path(__file__).resolve().parents[3]


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
