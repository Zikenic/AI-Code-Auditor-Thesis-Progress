"""GitHub PR Source Acquisition and Workspace Materialization.

Provides secure, isolated workspace materialization and diff acquisition
for GitHub Pull Request code audits.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from auditor.models.request import AuditRequest
from auditor.orchestration.interfaces import IDiffProvider

logger = logging.getLogger(__name__)

# Strict validation patterns
COMMIT_SHA_REGEX = re.compile(r"^[0-9a-fA-F]{40}$")
GITHUB_REPO_REGEX = re.compile(r"^(?:https:\/\/github\.com\/)?([a-zA-Z0-9_.-]+)\/([a-zA-Z0-9_.-]+?)(?:\.git)?\/?$")


class GitWorkspaceError(Exception):
    """Base exception for source acquisition and workspace materialization failures."""

    pass


class InvalidRepositoryError(GitWorkspaceError):
    """Raised when repository identifier or URL violates security or format constraints."""

    pass


class InvalidCommitShaError(GitWorkspaceError):
    """Raised when a commit SHA is malformed."""

    pass


class InvalidPrNumberError(GitWorkspaceError):
    """Raised when a pull request number is invalid."""

    pass


class CommitNotFoundError(GitWorkspaceError):
    """Raised when a specified commit SHA cannot be resolved or fetched."""

    pass


class GitCommandError(GitWorkspaceError):
    """Raised when an underlying Git command fails."""

    pass


class GitTimeoutError(GitWorkspaceError):
    """Raised when a Git command exceeds its execution timeout."""

    pass


@dataclass(frozen=True)
class MaterializedWorkspace:
    """Represents a materialized workspace checkout ready for analysis."""

    workspace_path: Path
    head_commit: str
    base_commit: str | None
    diff_content: str
    changed_files: list[str]


def _sanitize_error_text(text: str) -> str:
    """Sanitize error messages to prevent accidental leakage of tokens or credentials."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        text = text.replace(token, "[REDACTED]")
    # Scrub potential Authorization headers or embedded basic auth credentials
    text = re.sub(r"(?i)bearer\s+[a-zA-Z0-9_\-\.]+", "Bearer [REDACTED]", text)
    text = re.sub(r"(?i)basic\s+[a-zA-Z0-9_\-\.\+/=]+", "Basic [REDACTED]", text)
    text = re.sub(r"https?:\/\/[^@\/]+:[^@\/]+@", "https://[REDACTED]@", text)
    return text


def _remove_readonly(func: Any, path: str, exc_info: Any) -> None:
    """Error handler for shutil.rmtree on Windows to clear read-only attributes on Git files."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def _cleanup_directory(directory: str | Path) -> None:
    """Safely remove a directory tree, ensuring read-only Git objects are removed."""
    dir_path = Path(directory)
    if dir_path.exists():
        try:
            shutil.rmtree(dir_path, onerror=_remove_readonly)
        except Exception as e:
            logger.warning("Failed to remove temporary workspace directory %s: %s", dir_path, e)


def validate_commit_sha(sha: str | None, name: str = "commit") -> str | None:
    """Validate that a commit SHA is a 40-character hexadecimal string."""
    if sha is None:
        return None
    if not isinstance(sha, str) or not COMMIT_SHA_REGEX.match(sha.strip()):
        raise InvalidCommitShaError(
            f"Invalid {name} SHA format: '{sha}'. Must be a 40-character hexadecimal string."
        )
    return sha.strip().lower()


def validate_pr_number(pr_number: int | None) -> int | None:
    """Validate that PR number is a positive integer if provided."""
    if pr_number is None:
        return None
    if not isinstance(pr_number, int) or pr_number <= 0:
        raise InvalidPrNumberError(f"Invalid PR number: {pr_number}. Must be a positive integer.")
    return pr_number


def validate_repository(repository_id: str, allow_local_repos: bool = False) -> str:
    """Validate repository identifier and return normalized remote URL or canonical local path.

    Constraints:
    - In production (allow_local_repos=False), only GitHub repositories are allowed.
      Format: 'owner/repo' or 'https://github.com/owner/repo[.git]'.
    - Rejects non-GitHub hosts, file:// schemes, command injection characters, and path traversal.
    - If allow_local_repos=True (for offline tests), existing local directory paths are permitted.
    """
    if not repository_id or not isinstance(repository_id, str):
        raise InvalidRepositoryError("Repository identifier must be a non-empty string.")

    cleaned = repository_id.strip()

    # Reject dangerous characters
    if any(c in cleaned for c in (";", "&", "|", "`", "$", " ", "\n", "\r", "\t")):
        raise InvalidRepositoryError("Repository identifier contains forbidden characters.")

    if ".." in cleaned:
        raise InvalidRepositoryError("Path traversal sequences are forbidden.")

    # Check local repository path if explicitly permitted for testing
    if allow_local_repos:
        local_path = Path(cleaned)
        if local_path.is_dir() and (local_path / ".git").exists():
            return str(local_path.resolve())

    # Strictly validate GitHub repositories
    match = GITHUB_REPO_REGEX.match(cleaned)
    if not match:
        raise InvalidRepositoryError(
            f"Unsupported repository host or format: '{repository_id}'. "
            "Only GitHub repositories ('owner/repo' or 'https://github.com/owner/repo') are supported."
        )

    owner, repo = match.groups()
    if owner.startswith((".", "-")) or repo.startswith((".", "-")):
        raise InvalidRepositoryError("Repository owner and name must not start with '.' or '-'.")
    if ".." in owner or ".." in repo:
        raise InvalidRepositoryError("Path traversal sequences are forbidden.")

    return f"https://github.com/{owner}/{repo}.git"


class GitWorkspaceProvider:
    """Manages secure isolation, cloning/fetching, and workspace materialization."""

    def __init__(
        self,
        allow_local_repos: bool = False,
        timeout_seconds: int = 60,
    ):
        self.allow_local_repos = allow_local_repos
        self.timeout_seconds = timeout_seconds

    def _run_git(
        self,
        args: list[str],
        cwd: Path | str | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> str:
        """Run Git command safely via subprocess argument list (shell=False)."""
        cmd = ["git"] + args
        env = dict(os.environ)
        # Prevent git from interactively prompting for passwords or hanging
        env["GIT_TERMINAL_PROMPT"] = "0"
        if extra_env:
            env.update(extra_env)

        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd) if cwd else None,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                shell=False,
            )
        except subprocess.TimeoutExpired as te:
            raise GitTimeoutError(
                f"Git command timed out after {self.timeout_seconds} seconds: {' '.join(args[:2])}"
            ) from te
        except FileNotFoundError as fnf:
            raise GitCommandError("Git executable not found in system PATH.") from fnf

        if proc.returncode != 0:
            err = (proc.stderr or "").strip() or (proc.stdout or "").strip()
            sanitized = _sanitize_error_text(err)
            raise GitCommandError(f"Git command failed (exit code {proc.returncode}): {sanitized}")

        return proc.stdout or ""

    @contextmanager
    def materialize(
        self,
        repository_id: str,
        head_commit: str,
        base_commit: str | None = None,
        pr_number: int | None = None,
    ) -> Iterator[MaterializedWorkspace]:
        """Materialize PR source code into an isolated temporary workspace.

        Guarantees cleanup of temporary resources on both success and failure.
        """
        # 1. Validate inputs
        validated_repo = validate_repository(repository_id, allow_local_repos=self.allow_local_repos)
        validated_head = validate_commit_sha(head_commit, "head")
        assert validated_head is not None
        validated_base = validate_commit_sha(base_commit, "base")
        validated_pr = validate_pr_number(pr_number)

        temp_dir = tempfile.mkdtemp(prefix="auditor_ws_")
        temp_path = Path(temp_dir)

        try:
            # 2. Acquire source into temp_dir
            if self.allow_local_repos and Path(validated_repo).is_dir():
                self._materialize_local(validated_repo, temp_path, validated_head)
            else:
                self._materialize_remote(validated_repo, temp_path, validated_head, validated_base, validated_pr)

            # 3. Compute diff and modified file list
            diff_content, changed_files = self._compute_diff(temp_path, validated_head, validated_base)

            yield MaterializedWorkspace(
                workspace_path=temp_path,
                head_commit=validated_head,
                base_commit=validated_base,
                diff_content=diff_content,
                changed_files=changed_files,
            )

        finally:
            # Guaranteed cleanup
            _cleanup_directory(temp_dir)

    def _materialize_local(self, local_repo: str, target_dir: Path, head_sha: str) -> None:
        """Clone from a local repository fixture and checkout exact head_sha."""
        self._run_git(["clone", "--no-checkout", local_repo, str(target_dir)])
        try:
            self._run_git(["rev-parse", "--verify", f"{head_sha}^{{commit}}"], cwd=target_dir)
            self._run_git(["checkout", "--detach", head_sha], cwd=target_dir)
        except GitCommandError as e:
            raise CommitNotFoundError(f"Head commit {head_sha} not found in repository.") from e

    def _materialize_remote(
        self,
        remote_url: str,
        target_dir: Path,
        head_sha: str,
        base_sha: str | None,
        pr_number: int | None,
    ) -> None:
        """Initialize and fetch necessary commits from remote GitHub repository."""
        self._run_git(["init", str(target_dir)])
        self._run_git(["remote", "add", "origin", remote_url], cwd=target_dir)

        # Prepare authorization arguments if GITHUB_TOKEN is available
        token = os.environ.get("GITHUB_TOKEN")
        auth_args: list[str] = []
        if token:
            auth_args = ["-c", f"http.extraHeader=AUTHORIZATION: bearer {token}"]

        # Fetch strategy:
        # If PR number is given, fetch PR head ref
        fetched_head = False
        if pr_number is not None:
            try:
                self._run_git(
                    auth_args + ["fetch", "--depth=50", "origin", f"refs/pull/{pr_number}/head"],
                    cwd=target_dir,
                )
                fetched_head = True
            except GitCommandError as e:
                logger.warning("Could not fetch PR ref refs/pull/%s/head: %s", pr_number, e)

        # If head not fetched via PR ref, fetch commit directly
        if not fetched_head:
            try:
                self._run_git(auth_args + ["fetch", "--depth=50", "origin", head_sha], cwd=target_dir)
            except GitCommandError as e:
                raise CommitNotFoundError(f"Head commit {head_sha} could not be resolved from {remote_url}.") from e

        # Fetch base commit if specified
        if base_sha:
            try:
                self._run_git(auth_args + ["fetch", "--depth=50", "origin", base_sha], cwd=target_dir)
            except GitCommandError:
                # Attempt to deepen history if base is not reachable directly
                try:
                    self._run_git(auth_args + ["fetch", "--deepen=100", "origin"], cwd=target_dir)
                except GitCommandError:
                    pass

        # Verify and checkout head_sha
        try:
            self._run_git(["checkout", "--detach", head_sha], cwd=target_dir)
        except GitCommandError as e:
            raise CommitNotFoundError(f"Failed to checkout head commit {head_sha}.") from e

    def _compute_diff(
        self,
        workspace: Path,
        head_sha: str,
        base_sha: str | None,
    ) -> tuple[str, list[str]]:
        """Compute unified diff and changed file paths between base and head."""
        if base_sha:
            # Verify base_sha exists in local git repository
            try:
                self._run_git(["rev-parse", "--verify", f"{base_sha}^{{commit}}"], cwd=workspace)
            except GitCommandError as e:
                raise CommitNotFoundError(f"Base commit {base_sha} could not be resolved in repository.") from e

            diff_range = f"{base_sha}..{head_sha}"
            names_raw = self._run_git(["diff", "--name-only", diff_range], cwd=workspace)
            patch_raw = self._run_git(["diff", diff_range], cwd=workspace)
        else:
            # No base_sha provided; check if head has a parent commit
            has_parent = False
            try:
                self._run_git(["rev-parse", "--verify", f"{head_sha}~1^{{commit}}"], cwd=workspace)
                has_parent = True
            except GitCommandError:
                pass

            if has_parent:
                diff_range = f"{head_sha}~1..{head_sha}"
                names_raw = self._run_git(["diff", "--name-only", diff_range], cwd=workspace)
                patch_raw = self._run_git(["diff", diff_range], cwd=workspace)
            else:
                # Root commit: diff-tree against empty tree
                names_raw = self._run_git(
                    ["diff-tree", "--no-commit-id", "--name-only", "-r", head_sha],
                    cwd=workspace,
                )
                patch_raw = self._run_git(["show", head_sha], cwd=workspace)

        changed_files = [line.strip().replace("\\", "/") for line in names_raw.splitlines() if line.strip()]
        return patch_raw, changed_files


class GitDiffProvider(IDiffProvider):
    """Computes code diff and modified files from an existing checked-out Git workspace."""

    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    def get_diff(self, request: AuditRequest) -> tuple[str, list[str]]:
        """Extract diff and modified files from request.workspace_path."""
        if not request.workspace_path:
            raise GitWorkspaceError("AuditRequest workspace_path is not set; cannot compute diff.")

        ws = Path(request.workspace_path)
        if not ws.is_dir() or not (ws / ".git").exists():
            raise GitWorkspaceError(f"Workspace path '{request.workspace_path}' is not a valid Git directory.")

        head_sha = validate_commit_sha(request.head_commit, "head")
        assert head_sha is not None
        base_sha = validate_commit_sha(request.base_commit, "base")

        provider = GitWorkspaceProvider(allow_local_repos=True, timeout_seconds=self.timeout_seconds)
        return provider._compute_diff(ws, head_sha, base_sha)


class PrecomputedDiffProvider(IDiffProvider):
    """Adapter providing precomputed diff content and changed file list."""

    def __init__(self, diff_content: str, changed_files: list[str]):
        self.diff_content = diff_content
        self.changed_files = changed_files

    def get_diff(self, request: AuditRequest) -> tuple[str, list[str]]:
        """Return precomputed diff metadata."""
        return self.diff_content, list(self.changed_files)
