"""Comprehensive unit tests for GitHub PR source acquisition and workspace materialization."""

import subprocess
from pathlib import Path

import pytest

from auditor.models.request import AuditRequest
from auditor.orchestration.git_provider import (
    CommitNotFoundError,
    GitDiffProvider,
    GitTimeoutError,
    GitWorkspaceError,
    GitWorkspaceProvider,
    InvalidCommitShaError,
    InvalidPrNumberError,
    InvalidRepositoryError,
    PrecomputedDiffProvider,
    _sanitize_error_text,
    validate_commit_sha,
    validate_pr_number,
    validate_repository,
)


@pytest.fixture
def local_git_repo(tmp_path):
    """Create a temporary local git repository with two commits for testing."""
    repo_dir = tmp_path / "test_local_git_repo"
    repo_dir.mkdir()

    # Configure local git
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "auditor@test.local"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Auditor Tester"], cwd=repo_dir, check=True)

    # Base commit
    file1 = repo_dir / "module_a.py"
    file1.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)
    base_sha = (
        subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True)
        .stdout.strip()
    )

    # Head commit: modify file1 and add file2 with vulnerable code
    file1.write_text("def add(a, b):\n    # updated\n    return a + b\n", encoding="utf-8")
    file2 = repo_dir / "vuln.py"
    file2.write_text("import os\nos.system('echo vulnerable')\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Add vulnerable code"], cwd=repo_dir, check=True)
    head_sha = (
        subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True)
        .stdout.strip()
    )

    return {"dir": repo_dir, "base_sha": base_sha, "head_sha": head_sha}


class TestValidation:
    """Test validation of repositories, commit SHAs, and PR numbers."""

    def test_validate_repository_valid_github(self):
        # owner/repo format
        url1 = validate_repository("Zikenic/AI-Code-Auditor-Thesis1")
        assert url1 == "https://github.com/Zikenic/AI-Code-Auditor-Thesis1.git"

        # full https url
        url2 = validate_repository("https://github.com/octocat/Hello-World")
        assert url2 == "https://github.com/octocat/Hello-World.git"

        # with .git suffix
        url3 = validate_repository("https://github.com/octocat/Hello-World.git")
        assert url3 == "https://github.com/octocat/Hello-World.git"

    def test_validate_repository_disallowed_hosts(self):
        with pytest.raises(InvalidRepositoryError, match="Unsupported repository host or format"):
            validate_repository("https://gitlab.com/owner/repo.git")

        with pytest.raises(InvalidRepositoryError, match="Unsupported repository host or format"):
            validate_repository("https://bitbucket.org/owner/repo.git")

        with pytest.raises(InvalidRepositoryError, match="Unsupported repository host or format"):
            validate_repository("https://malicious-domain.com/owner/repo")

    def test_validate_repository_dangerous_patterns(self):
        with pytest.raises(InvalidRepositoryError, match="contains forbidden characters"):
            validate_repository("owner/repo; rm -rf /")

        with pytest.raises(InvalidRepositoryError, match="contains forbidden characters"):
            validate_repository("owner/repo$(whoami)")

        with pytest.raises(InvalidRepositoryError, match="contains forbidden characters"):
            validate_repository("owner/repo`id`")

        with pytest.raises(InvalidRepositoryError, match="Path traversal"):
            validate_repository("owner/../../etc/passwd")

        with pytest.raises(InvalidRepositoryError, match="must not start with"):
            validate_repository("-owner/repo")

    def test_validate_repository_local_controls(self, tmp_path):
        git_dir = tmp_path / "my_git"
        git_dir.mkdir()
        (git_dir / ".git").mkdir()

        # Disallowed by default (production safety)
        with pytest.raises(InvalidRepositoryError):
            validate_repository(str(git_dir), allow_local_repos=False)

        # Allowed when allow_local_repos=True
        validated = validate_repository(str(git_dir), allow_local_repos=True)
        assert Path(validated).resolve() == git_dir.resolve()

    def test_validate_commit_sha(self):
        valid = "a" * 40
        assert validate_commit_sha(valid) == valid
        assert validate_commit_sha(None) is None

        # Invalid lengths and characters
        with pytest.raises(InvalidCommitShaError):
            validate_commit_sha("shortsha")

        with pytest.raises(InvalidCommitShaError):
            validate_commit_sha("g" * 40)

        with pytest.raises(InvalidCommitShaError):
            validate_commit_sha("a" * 39 + ";")

        with pytest.raises(InvalidCommitShaError):
            validate_commit_sha("a" * 41)

    def test_validate_pr_number(self):
        assert validate_pr_number(1) == 1
        assert validate_pr_number(105) == 105
        assert validate_pr_number(None) is None

        with pytest.raises(InvalidPrNumberError):
            validate_pr_number(0)

        with pytest.raises(InvalidPrNumberError):
            validate_pr_number(-5)

        with pytest.raises(InvalidPrNumberError):
            validate_pr_number("not_an_int")  # type: ignore


class TestSanitization:
    """Test secret scrubbing and credential safety."""

    def test_sanitize_error_text_with_github_token(self, monkeypatch):
        token = "ghp_1234567890abcdefghijklmnopqrstuvwxyz"
        monkeypatch.setenv("GITHUB_TOKEN", token)

        raw = f"fatal: unable to access 'https://github.com/repo': 401 Unauthorized with token {token}"
        sanitized = _sanitize_error_text(raw)
        assert token not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_error_text_with_bearer_headers(self):
        raw = "Header sent: Authorization: Bearer secret_access_token_xyz"
        sanitized = _sanitize_error_text(raw)
        assert "secret_access_token_xyz" not in sanitized
        assert "Bearer [REDACTED]" in sanitized

    def test_sanitize_error_text_with_embedded_credentials(self):
        raw = "clone failed for https://user:super_secret@github.com/repo.git"
        sanitized = _sanitize_error_text(raw)
        assert "super_secret" not in sanitized
        assert "https://[REDACTED]@github.com/repo.git" in sanitized


class TestWorkspaceMaterialization:
    """Test git workspace materialization, diff extraction, and cleanup guarantees."""

    def test_materialize_local_repo_success(self, local_git_repo):
        provider = GitWorkspaceProvider(allow_local_repos=True)
        repo_dir = local_git_repo["dir"]
        base_sha = local_git_repo["base_sha"]
        head_sha = local_git_repo["head_sha"]

        captured_ws_path = None
        with provider.materialize(
            repository_id=str(repo_dir),
            head_commit=head_sha,
            base_commit=base_sha,
        ) as ws:
            captured_ws_path = ws.workspace_path
            assert ws.workspace_path.is_dir()
            assert ws.head_commit == head_sha
            assert ws.base_commit == base_sha

            # Files in head commit exist
            assert (ws.workspace_path / "module_a.py").exists()
            assert (ws.workspace_path / "vuln.py").exists()

            # Changed files correctly detected
            assert "module_a.py" in ws.changed_files
            assert "vuln.py" in ws.changed_files

            # Diff content verified
            assert "os.system" in ws.diff_content
            assert "def add(a, b):" in ws.diff_content

        # Guaranteed cleanup verification
        assert captured_ws_path is not None
        assert not captured_ws_path.exists()

    def test_materialize_guaranteed_cleanup_on_exception(self, local_git_repo):
        provider = GitWorkspaceProvider(allow_local_repos=True)
        repo_dir = local_git_repo["dir"]
        head_sha = local_git_repo["head_sha"]

        captured_ws_path = None
        with pytest.raises(RuntimeError, match="Simulated processing crash"):
            with provider.materialize(
                repository_id=str(repo_dir),
                head_commit=head_sha,
            ) as ws:
                captured_ws_path = ws.workspace_path
                assert captured_ws_path.is_dir()
                raise RuntimeError("Simulated processing crash")

        # Must still be cleaned up
        assert captured_ws_path is not None
        assert not captured_ws_path.exists()

    def test_materialize_missing_commit(self, local_git_repo):
        provider = GitWorkspaceProvider(allow_local_repos=True)
        repo_dir = local_git_repo["dir"]
        missing_sha = "0" * 40

        with pytest.raises(CommitNotFoundError):
            with provider.materialize(
                repository_id=str(repo_dir),
                head_commit=missing_sha,
            ):
                pass

    def test_materialize_timeout(self, monkeypatch, local_git_repo):
        # Set an extremely low timeout to test timeout handling
        provider = GitWorkspaceProvider(allow_local_repos=True, timeout_seconds=0.0001)
        repo_dir = local_git_repo["dir"]
        head_sha = local_git_repo["head_sha"]

        with pytest.raises(GitTimeoutError):
            with provider.materialize(
                repository_id=str(repo_dir),
                head_commit=head_sha,
            ):
                pass

    def test_materialize_utf8_diff_content(self, tmp_path):
        """Verify that diffs containing non-ASCII / UTF-8 characters do not crash on Windows locale decoding."""
        repo_dir = tmp_path / "utf8_git_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.local"], cwd=repo_dir, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)

        f = repo_dir / "unicode_test.py"
        f.write_text("# Initial ASCII\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=repo_dir, check=True)
        base_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True).stdout.strip()

        # Add Vietnamese, math symbols, smart quotes
        f.write_text("# Tiếng Việt có dấu, ký tự đặc biệt: ± ≥ ≤, smart quotes “ ” ‘ ’\nprint('hello')\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
        subprocess.run(["git", "commit", "-m", "Unicode commit"], cwd=repo_dir, check=True)
        head_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, check=True, capture_output=True, text=True).stdout.strip()

        provider = GitWorkspaceProvider(allow_local_repos=True)
        with provider.materialize(repository_id=str(repo_dir), head_commit=head_sha, base_commit=base_sha) as ws:
            assert "Tiếng Việt" in ws.diff_content
            assert "unicode_test.py" in ws.changed_files


class TestDiffProviders:
    """Test GitDiffProvider and PrecomputedDiffProvider."""

    def test_git_diff_provider_success(self, local_git_repo):
        provider = GitWorkspaceProvider(allow_local_repos=True)
        repo_dir = local_git_repo["dir"]
        base_sha = local_git_repo["base_sha"]
        head_sha = local_git_repo["head_sha"]

        with provider.materialize(
            repository_id=str(repo_dir),
            head_commit=head_sha,
            base_commit=base_sha,
        ) as ws:
            diff_provider = GitDiffProvider()
            req = AuditRequest(
                request_id="req-test-diff",
                repository_id="local/test",
                head_commit=head_sha,
                base_commit=base_sha,
                workspace_path=str(ws.workspace_path),
            )
            diff_content, changed_files = diff_provider.get_diff(req)
            assert "vuln.py" in changed_files
            assert "os.system" in diff_content

    def test_git_diff_provider_missing_workspace(self):
        diff_provider = GitDiffProvider()
        req = AuditRequest(
            request_id="req-missing-ws",
            repository_id="local/test",
            head_commit="a" * 40,
            workspace_path=None,
        )
        with pytest.raises(GitWorkspaceError, match="workspace_path is not set"):
            diff_provider.get_diff(req)

    def test_precomputed_diff_provider(self):
        precomputed = PrecomputedDiffProvider("SAMPLE-PATCH-123", ["file_x.py"])
        req = AuditRequest(
            request_id="req-prec",
            repository_id="local/test",
            head_commit="a" * 40,
        )
        diff, files = precomputed.get_diff(req)
        assert diff == "SAMPLE-PATCH-123"
        assert files == ["file_x.py"]
