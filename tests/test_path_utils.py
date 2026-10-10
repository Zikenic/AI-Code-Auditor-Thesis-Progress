"""Unit tests for path normalization and repository-relative path matching."""

from auditor.matcher.path_utils import normalize_repo_path


class TestPathNormalization:
    def test_windows_backslashes_normalized_to_forward_slashes(self):
        assert normalize_repo_path("src\\auditor\\matcher\\engine.py") == "src/auditor/matcher/engine.py"
        assert normalize_repo_path("tests\\test_matcher.py") == "tests/test_matcher.py"

    def test_leading_slashes_and_dots_stripped(self):
        assert normalize_repo_path("/src/module.py") == "src/module.py"
        assert normalize_repo_path("///src/module.py") == "src/module.py"
        assert normalize_repo_path("./src/module.py") == "src/module.py"
        assert normalize_repo_path("././src/module.py") == "src/module.py"

    def test_internal_relative_components_resolved(self):
        assert normalize_repo_path("src/sub/../module.py") == "src/module.py"
        assert normalize_repo_path("src/./module.py") == "src/module.py"

    def test_safe_repo_root_prefix_removal(self):
        assert normalize_repo_path("my-repo/src/main.py", repo_root_prefix="my-repo") == "src/main.py"
        assert normalize_repo_path("my-repo/src/main.py", repo_root_prefix="my-repo/") == "src/main.py"
        assert normalize_repo_path("/workspace/repo/app.py", repo_root_prefix="/workspace/repo") == "app.py"

    def test_no_basename_fallback(self):
        """Verify that paths with identical filenames in different directories do not match."""
        p1 = normalize_repo_path("src/utils.py")
        p2 = normalize_repo_path("tests/utils.py")
        assert p1 != p2
        assert p1 == "src/utils.py"
        assert p2 == "tests/utils.py"

    def test_empty_and_whitespace_paths(self):
        assert normalize_repo_path("") == ""
        assert normalize_repo_path("   ") == ""
        assert normalize_repo_path(".") == ""
