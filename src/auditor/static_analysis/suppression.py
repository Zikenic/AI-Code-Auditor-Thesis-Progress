"""Repository-controlled suppression isolation utilities.

Enforces frozen operational policy FR-03:
The primary benchmark scoring path strictly isolates against target-repository
configurations (ruff.toml, pyproject.toml), ignore files (.semgrepignore, .gitignore),
and inline suppression comments (# noqa, # nosemgrep) from silently hiding findings.
"""

from __future__ import annotations

import io
import re
import tempfile
import tokenize
from pathlib import Path

# Regex to detect and neutralize inline suppression directives
SUPPRESSION_PATTERN = re.compile(
    r"#\s*(noqa|nosemgrep|nosem|ruff:\s*noqa|flake8:\s*noqa)",
    re.IGNORECASE,
)


def neutralize_inline_suppressions(source_code: str) -> str:
    """Neutralize inline # noqa and # nosemgrep directives while preserving line and column coordinates.

    Replaces suppression keywords with an underscore prefix (e.g., '# _noqa', '# _nosemgrep')
    so that linters and AST scanners do not treat them as suppression directives, while
    preserving exact line counts, line coordinates, and non-comment byte offsets.
    Does not modify string literals that happen to contain suppression patterns.
    """

    def _replacer(match: re.Match[str]) -> str:
        text = match.group(0)
        # Prefix the keyword inside the comment with underscore
        return re.sub(
            r"(noqa|nosemgrep|nosem)",
            r"_\1",
            text,
            flags=re.IGNORECASE,
        )

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source_code).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Fallback to regex replacement if tokenization fails
        return SUPPRESSION_PATTERN.sub(_replacer, source_code)

    comment_lines: dict[int, tuple[int, str]] = {}
    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            row, col = tok.start
            comment_lines[row] = (col, tok.string)

    if not comment_lines:
        return source_code

    lines = source_code.splitlines(keepends=True)
    out_lines: list[str] = []
    for idx, line in enumerate(lines, 1):
        if idx in comment_lines:
            col, orig_comment = comment_lines[idx]
            prefix = line[:col]
            rest = line[col:]
            if rest.startswith(orig_comment):
                neutralized_comment = SUPPRESSION_PATTERN.sub(_replacer, orig_comment)
                rest = neutralized_comment + rest[len(orig_comment) :]
            else:
                rest = SUPPRESSION_PATTERN.sub(_replacer, rest)
            out_lines.append(prefix + rest)
        else:
            out_lines.append(line)

    return "".join(out_lines)


class ControlledSourceWorkspace:
    """Creates and manages an isolated temporary workspace containing controlled source file copies.

    Properties:
    1. Only requested files are copied.
    2. Target repository configurations (ruff.toml, pyproject.toml) are NOT copied.
    3. Target repository ignore files (.semgrepignore, .gitignore) are NOT copied.
    4. Inline suppression directives in source copies are neutralized.
    5. Relative repository file paths and exact line coordinates are strictly preserved.
    """

    def __init__(
        self,
        workspace_path: str | Path | None,
        relative_files: list[str],
    ):
        self.workspace_path = Path(workspace_path) if workspace_path else Path.cwd()
        self.relative_files = relative_files
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self.isolated_root: Path | None = None
        self.copied_files: list[Path] = []

    def __enter__(self) -> ControlledSourceWorkspace:
        self._temp_dir = tempfile.TemporaryDirectory(prefix="auditor_isolated_")
        self.isolated_root = Path(self._temp_dir.name)

        for rel_str in self.relative_files:
            rel_path = Path(rel_str)
            src_file = self.workspace_path / rel_path
            if not src_file.exists() or not src_file.is_file():
                continue

            target_file = self.isolated_root / rel_path
            target_file.parent.mkdir(parents=True, exist_ok=True)

            try:
                content = src_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                content = src_file.read_text(encoding="latin-1", errors="replace")

            neutralized = neutralize_inline_suppressions(content)
            target_file.write_text(neutralized, encoding="utf-8")
            self.copied_files.append(target_file)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._temp_dir = None
            self.isolated_root = None
            self.copied_files = []
