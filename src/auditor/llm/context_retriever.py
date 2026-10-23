"""Repository-level context retriever for Configuration D (Option B: AST Symbol Graph + Lexical Search)."""

from __future__ import annotations

import ast
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from auditor.llm.chunker import default_token_estimator


@dataclass(frozen=True)
class ContextItem:
    file_path: str
    start_line: int
    end_line: int
    content: str
    symbol_name: str
    priority: int  # 1: Direct AST import/call, 2: Base class, 3: Lexical match


class RepositoryIndex:
    """In-memory index of Python source files extracted strictly at the pre-fix commit C_buggy."""

    def __init__(self, repo_dir: str | Path, commit_hash: str):
        self.repo_dir = Path(repo_dir)
        self.commit_hash = commit_hash
        self.files: dict[str, str] = {}  # rel_path -> full_text
        self.symbol_table: dict[str, list[tuple[str, int, int]]] = {}  # symbol_name -> list of (file, start, end)
        self.classes: dict[str, tuple[str, int, int, list[str]]] = {}  # class_name -> (file, start, end, base_classes)
        self._build_index()

    def _build_index(self) -> None:
        """Extract and index all .py files in git tree at commit_hash using fast git archive, or fallback to directory."""
        import io
        import tarfile

        try:
            res = subprocess.run(
                ["git", "-C", str(self.repo_dir), "archive", self.commit_hash],
                capture_output=True,
                check=True,
            )
            bio = io.BytesIO(res.stdout)
            with tarfile.open(fileobj=bio) as tar:
                for member in tar.getmembers():
                    name = member.name
                    if not name.endswith(".py"):
                        continue
                    parts = name.split("/")
                    if any(
                        part in parts
                        for part in ["tests", "testing", "test", "docs", "doc", "build", "dist", "migrations", ".github"]
                    ):
                        continue
                    if parts[-1].startswith("test_") or parts[-1].endswith("_test.py"):
                        continue

                    f = tar.extractfile(member)
                    if f:
                        content = f.read().decode("utf-8", errors="replace")
                        self.files[name] = content
                        self._index_file_ast(name, content)
        except Exception:
            # Fallback: Index local .py files directly from self.repo_dir
            if self.repo_dir.exists():
                for py_path in self.repo_dir.rglob("*.py"):
                    name = str(py_path.relative_to(self.repo_dir)).replace("\\", "/")
                    parts = name.split("/")
                    if any(
                        part in parts
                        for part in ["tests", "testing", "test", "docs", "doc", "build", "dist", "migrations", ".github"]
                    ):
                        continue
                    if parts[-1].startswith("test_") or parts[-1].endswith("_test.py"):
                        continue
                    try:
                        content = py_path.read_text(encoding="utf-8", errors="replace")
                        self.files[name] = content
                        self._index_file_ast(name, content)
                    except Exception:
                        pass

    def _index_file_ast(self, rel_path: str, content: str) -> None:
        """Parse top-level classes and functions in AST."""
        try:
            tree = ast.parse(content)
        except Exception:
            return  # Skip unparseable files gracefully

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                s_line = node.lineno
                e_line = getattr(node, "end_lineno", s_line + 20)
                self.symbol_table.setdefault(node.name, []).append((rel_path, s_line, e_line))
            elif isinstance(node, ast.ClassDef):
                s_line = node.lineno
                e_line = getattr(node, "end_lineno", s_line + 40)
                bases = []
                for b in node.bases:
                    if isinstance(b, ast.Name):
                        bases.append(b.id)
                    elif isinstance(b, ast.Attribute):
                        bases.append(b.attr)
                self.classes[node.name] = (rel_path, s_line, e_line, bases)
                self.symbol_table.setdefault(node.name, []).append((rel_path, s_line, e_line))

                # Also index methods inside class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        m_s = item.lineno
                        m_e = getattr(item, "end_lineno", m_s + 20)
                        self.symbol_table.setdefault(item.name, []).append((rel_path, m_s, m_e))


class RepositoryContextRetriever:
    """Mechanical context retriever enforcing all Config D constraints."""

    def __init__(self, index: RepositoryIndex, token_counter: Callable[[str], int] | None = None):
        self.index = index
        self.token_counter = token_counter

    def retrieve_context(
        self,
        target_file: str,
        chunk_start: int,
        chunk_end: int,
        chunk_code: str,
        max_tokens: int = 4000,
        token_counter: Callable[[str], int] | None = None,
    ) -> tuple[str, list[ContextItem], int]:
        """Retrieve deduplicated, ranked repository context items within the token budget."""
        # 1. Derive queries strictly from the chunk's code
        imported_symbols, called_symbols, class_bases = self._extract_chunk_queries(chunk_code)

        candidates: list[ContextItem] = []
        seen_keys: set[tuple[str, int, int]] = set()

        # Hard Rule: Target chunk itself is strictly forbidden
        target_key = (target_file, chunk_start, chunk_end)
        seen_keys.add(target_key)

        # Priority 1: Direct AST resolution of imported symbols & called symbols
        for sym in imported_symbols | called_symbols:
            if sym in self.index.symbol_table:
                for fpath, s_line, e_line in self.index.symbol_table[sym]:
                    # Exclude active target chunk or same-file overlap
                    if fpath == target_file and not (e_line < chunk_start or s_line > chunk_end):
                        continue
                    key = (fpath, s_line, e_line)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    snippet = self._extract_snippet(fpath, s_line, e_line)
                    if snippet:
                        candidates.append(
                            ContextItem(
                                file_path=fpath,
                                start_line=s_line,
                                end_line=e_line,
                                content=snippet,
                                symbol_name=sym,
                                priority=1,
                            )
                        )

        # Priority 2: Base classes
        for base in class_bases:
            if base in self.index.classes:
                fpath, s_line, e_line, _ = self.index.classes[base]
                if fpath == target_file and not (e_line < chunk_start or s_line > chunk_end):
                    continue
                key = (fpath, s_line, e_line)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                snippet = self._extract_snippet(fpath, s_line, e_line)
                if snippet:
                    candidates.append(
                        ContextItem(
                            file_path=fpath,
                            start_line=s_line,
                            end_line=e_line,
                            content=snippet,
                            symbol_name=base,
                            priority=2,
                        )
                    )

        # Priority 3: Lexical match on external files for called functions
        if len(candidates) < 3:
            for sym in list(called_symbols)[:5]:
                # find files that define `def sym(`
                pattern = f"def {sym}("
                for fpath, fcontent in self.index.files.items():
                    if fpath == target_file:
                        continue
                    if pattern in fcontent:
                        lines = fcontent.splitlines()
                        for i, line in enumerate(lines):
                            if pattern in line:
                                s_line = i + 1
                                e_line = min(len(lines), s_line + 30)
                                key = (fpath, s_line, e_line)
                                if key in seen_keys:
                                    continue
                                seen_keys.add(key)
                                snippet = self._extract_snippet(fpath, s_line, e_line)
                                if snippet:
                                    candidates.append(
                                        ContextItem(
                                            file_path=fpath,
                                            start_line=s_line,
                                            end_line=e_line,
                                            content=snippet,
                                            symbol_name=sym,
                                            priority=3,
                                        )
                                    )
                                break

        # Deterministic sorting: priority asc, then file_path asc, then start_line asc
        candidates.sort(key=lambda c: (c.priority, c.file_path, c.start_line))

        # Budget packing (B_context <= max_tokens)
        accepted: list[ContextItem] = []
        current_tokens = 0
        omitted_count = 0

        counter = token_counter or self.token_counter or default_token_estimator
        for item in candidates:
            # Render item
            item_text = self._render_context_item(item)
            item_tokens = counter(item_text)

            if current_tokens + item_tokens <= max_tokens:
                accepted.append(item)
                current_tokens += item_tokens
            else:
                omitted_count += 1

        if not accepted:
            return "", [], 0

        # Format final context section
        rendered_parts = [
            "### REPOSITORY CONTEXT EXCERPTS (FOR REFERENCE ONLY)",
            "The following code excerpts from the repository are provided for reference. They may be irrelevant to the current issue. Review the active AUDIT TARGET code independently and use the excerpts only when they provide useful evidence about definitions, type contracts, or callers.\n",
        ]

        for item in accepted:
            rendered_parts.append(self._render_context_item(item))

        if omitted_count > 0:
            rendered_parts.append(f"[Notice: {omitted_count} additional context excerpts omitted]")

        rendered_parts.append(
            "\nNote: Cite line numbers only from the active AUDIT TARGET file, never from the repository context excerpts."
        )

        return "\n\n".join(rendered_parts), accepted, omitted_count

    def _extract_chunk_queries(self, chunk_code: str) -> tuple[set[str], set[str], set[str]]:
        """Mechanically extract imports, calls, and class bases from chunk code."""
        imported_symbols: set[str] = set()
        called_symbols: set[str] = set()
        class_bases: set[str] = set()

        # Strip line numbers prefix if present (<num>: <code>)
        clean_lines = []
        for line in chunk_code.splitlines():
            clean_lines.append(re.sub(r"^\s*\d+:\s?", "", line))
        clean_code = "\n".join(clean_lines)

        try:
            tree = ast.parse(clean_code)
        except Exception:
            # Fallback regex extraction if chunk has partial syntax
            for line in clean_lines:
                m_imp = re.search(r"import\s+([A-Za-z0-9_]+)", line)
                if m_imp:
                    imported_symbols.add(m_imp.group(1))
                m_call = re.findall(r"([A-Za-z0-9_]+)\(", line)
                called_symbols.update(m_call)
            return imported_symbols, called_symbols, class_bases

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_symbols.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported_symbols.add(alias.name)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    called_symbols.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    called_symbols.add(node.func.attr)
            elif isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        class_bases.add(base.id)
                    elif isinstance(base, ast.Attribute):
                        class_bases.add(base.attr)

        return imported_symbols, called_symbols, class_bases

    def _extract_snippet(self, rel_path: str, start_line: int, end_line: int) -> str | None:
        """Extract line-prefixed code snippet from repository file."""
        content = self.index.files.get(rel_path)
        if not content:
            return None
        lines = content.splitlines()
        s_idx = max(0, start_line - 1)
        e_idx = min(len(lines), end_line)

        snippet_lines = [f"{s_idx + i + 1}: {lines[s_idx + i]}" for i in range(e_idx - s_idx)]
        return "\n".join(snippet_lines)

    def _render_context_item(self, item: ContextItem) -> str:
        return (
            f"--- CONTEXT: {item.file_path} (Lines {item.start_line} to {item.end_line}) ---\n"
            f"{item.content}\n"
            f"--- END CONTEXT ---"
        )
