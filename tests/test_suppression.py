"""Unit tests for repository-controlled suppression isolation."""

import tempfile
from pathlib import Path

from auditor.static_analysis.suppression import (
    ControlledSourceWorkspace,
    neutralize_inline_suppressions,
)


def test_neutralize_inline_suppressions_noqa():
    code = 'password = "admin"  # noqa: S105\nprint(password)  # noqa\n'
    neutralized = neutralize_inline_suppressions(code)

    assert "noqa" not in neutralized.lower() or "_noqa" in neutralized.lower()
    assert "# _noqa: S105" in neutralized or "# _noqa" in neutralized
    # Ensure line count is preserved
    assert len(code.splitlines()) == len(neutralized.splitlines())


def test_neutralize_inline_suppressions_nosemgrep():
    code = "os.system(cmd)  # nosemgrep: rule-id\ncursor.execute(sql)  # nosemgrep\n"
    neutralized = neutralize_inline_suppressions(code)

    assert "# _nosemgrep" in neutralized
    assert len(code.splitlines()) == len(neutralized.splitlines())


def test_neutralize_preserves_regular_comments():
    code = "# This is a normal comment\nx = 10  # another comment\n"
    neutralized = neutralize_inline_suppressions(code)

    assert neutralized == code


def test_neutralize_preserves_string_literals():
    code = (
        'msg = "# noqa inside single-line string"\n'
        'query = "SELECT * FROM users WHERE 1=1 # nosem"\n'
        'doc = """\nThis docstring mentions # nosemgrep and # ruff: noqa\n"""\n'
        "x = 10  # noqa: S101\n"
    )
    neutralized = neutralize_inline_suppressions(code)

    # String literals must remain untouched
    assert 'msg = "# noqa inside single-line string"' in neutralized
    assert 'query = "SELECT * FROM users WHERE 1=1 # nosem"' in neutralized
    assert "This docstring mentions # nosemgrep and # ruff: noqa" in neutralized

    # Actual comment must be neutralized
    assert "x = 10  # _noqa: S101" in neutralized


def test_neutralize_short_nosem():
    code = "import os\nos.system('ls')  # nosem\nos.system('pwd')  # nosem: python.lang.security.audit\n"
    neutralized = neutralize_inline_suppressions(code)

    assert "# _nosem\n" in neutralized
    assert "# _nosem: python.lang.security.audit" in neutralized


def test_neutralize_file_level_ruff_noqa():
    code = "# ruff: noqa\n# ruff: noqa: S101,B006\ndef foo(): pass\n"
    neutralized = neutralize_inline_suppressions(code)

    assert "# ruff: _noqa\n" in neutralized
    assert "# ruff: _noqa: S101,B006\n" in neutralized


def test_neutralize_flake8_noqa():
    code = "x = 1  # flake8: noqa\ny = 2  # flake8: noqa: E501\n"
    neutralized = neutralize_inline_suppressions(code)

    assert "# flake8: _noqa\n" in neutralized
    assert "# flake8: _noqa: E501" in neutralized


def test_neutralize_rule_specific_nosemgrep_and_noqa_variants():
    code = (
        "query = sql  # nosemgrep: python.lang.security.audit.formatted-sql-query\n"
        "cursor.execute(raw)  # nosem: python.django.security.injection.raw-sql\n"
        "assert cond  # noqa: S101,B006,F601\n"
    )
    neutralized = neutralize_inline_suppressions(code)

    assert "# _nosemgrep: python.lang.security.audit.formatted-sql-query" in neutralized
    assert "# _nosem: python.django.security.injection.raw-sql" in neutralized
    assert "# _noqa: S101,B006,F601" in neutralized


def test_controlled_source_workspace_isolation():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)

        # Create source files
        src_py = root / "src" / "app.py"
        src_py.parent.mkdir(parents=True, exist_ok=True)
        src_py.write_text('key = "secret"  # noqa: S105\n', encoding="utf-8")

        # Create adversarial repository configs including per-file-ignores that should NOT be copied
        (root / "ruff.toml").write_text(
            '[lint]\nignore = ["S105"]\n[lint.per-file-ignores]\n"src/app.py" = ["S105"]\n',
            encoding="utf-8",
        )
        (root / "pyproject.toml").write_text(
            '[tool.ruff.lint]\nignore = ["S105"]\n[tool.ruff.lint.per-file-ignores]\n"src/app.py" = ["S105"]\n',
            encoding="utf-8",
        )
        (root / ".semgrepignore").write_text("src/**\n", encoding="utf-8")
        (root / ".gitignore").write_text("src/**\n", encoding="utf-8")

        with ControlledSourceWorkspace(root, ["src/app.py"]) as ws:
            isolated_root = ws.isolated_root
            assert isolated_root is not None
            assert len(ws.copied_files) == 1

            # Assert repo config and ignore files were NOT copied
            assert not (isolated_root / "ruff.toml").exists()
            assert not (isolated_root / "pyproject.toml").exists()
            assert not (isolated_root / ".semgrepignore").exists()
            assert not (isolated_root / ".gitignore").exists()

            # Assert source file was copied with suppressions neutralized
            copied_app = isolated_root / "src" / "app.py"
            assert copied_app.exists()
            content = copied_app.read_text(encoding="utf-8")
            assert "# _noqa: S105" in content

        # On exit, temp directory is cleaned up
        assert not isolated_root.exists()
