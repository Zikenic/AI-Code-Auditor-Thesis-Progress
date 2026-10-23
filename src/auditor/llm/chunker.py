"""Hierarchical chunking policy for Python source code under fixed token budgets.

Adheres strictly to Project Documents/dataset/configuration_input_protocol.md:
- Tier 1: Single-pass whole-file audit if rendered tokens <= 16,000.
- Tier 2: Syntax-aware AST chunking (preserving preamble imports/constants, grouping top-level classes/functions).
- Tier 3: Intra-component / fallback chunking with deterministic N=100 lines overlap.
- Enforces INV-02 (Ground-Truth Agnosticism) and INV-03 (Complete Line Coverage).
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceChunk:
    """A deterministic chunk of a target source file for auditing."""

    file_path: str
    chunk_index: int
    total_chunks: int
    start_line: int
    end_line: int
    total_lines: int
    rendered_text: str
    raw_code: str
    token_estimate: int
    tier: int  # 1, 2, or 3
    scope_description: str
    token_count_method: str = "tokenizer"


def default_token_estimator(text: str) -> int:
    """Fallback heuristic token estimator used ONLY when official tokenizer is unavailable.

    Approximates tokens as character count / 3.2 with a minimum of words count.
    Provides safety margin over the standard 3.5-4.0 characters/token ratio.
    NOTE: This is a fallback heuristic approximation and must NOT masquerade
    as an authoritative tokenizer measurement.
    """
    by_chars = int(len(text) / 3.2) + 1
    by_words = int(len(text.split()) * 1.25) + 1
    return max(by_chars, by_words)


def render_source_lines(
    lines: list[str],
    start_line: int,
    end_line: int,
    file_path: str,
    total_lines: int,
    preamble_lines: list[tuple[int, str]] | None = None,
) -> str:
    """Render source lines with 1-indexed line prefixes and canonical header/footer."""
    header = f"=== AUDIT TARGET: {file_path} (Lines {start_line} to {end_line} of {total_lines}) ===\n"
    rendered_parts: list[str] = [header]

    if preamble_lines:
        rendered_parts.append("# --- SHARED PREAMBLE (IMPORTS & CONSTANTS) ---\n")
        for line_no, content in preamble_lines:
            rendered_parts.append(f"{line_no}: {content}")
        rendered_parts.append("# --- AUDIT BODY ---\n")

    for i in range(start_line - 1, end_line):
        line_num = i + 1
        rendered_parts.append(f"{line_num}: {lines[i]}")

    rendered_parts.append(f"=== END AUDIT TARGET: {file_path} ===\n")
    return "".join(rendered_parts)


class SourceChunker:
    """Deterministic, ground-truth-agnostic hierarchical source chunker."""

    def __init__(
        self,
        token_budget: int = 16_000,
        token_counter: Callable[[str], int] | None = None,
        tier3_overlap: int = 100,
        token_count_method: str | None = None,
    ):
        self.token_budget = token_budget
        if token_counter is not None:
            self.count_tokens = token_counter
            self.token_count_method = token_count_method or "tokenizer"
        else:
            self.count_tokens = default_token_estimator
            self.token_count_method = token_count_method or "fallback_heuristic"
        self.tier3_overlap = tier3_overlap

    def chunk_source(self, raw_source: str, file_path: str) -> list[SourceChunk]:
        """Split raw Python source code into deterministic chunks satisfying the token budget."""
        if not raw_source.endswith("\n"):
            raw_source += "\n"

        lines = raw_source.splitlines(keepends=True)
        total_lines = len(lines)

        if total_lines == 0:
            return []

        # 1. Evaluate Tier 1: Single-pass whole-file check
        full_rendered = render_source_lines(lines, 1, total_lines, file_path, total_lines)
        full_tokens = self.count_tokens(full_rendered)

        if full_tokens <= self.token_budget:
            return [
                SourceChunk(
                    file_path=file_path,
                    chunk_index=1,
                    total_chunks=1,
                    start_line=1,
                    end_line=total_lines,
                    total_lines=total_lines,
                    rendered_text=full_rendered,
                    raw_code=raw_source,
                    token_estimate=full_tokens,
                    tier=1,
                    scope_description="Whole file (Tier 1 single-pass)",
                    token_count_method=self.token_count_method,
                )
            ]

        # 2. Evaluate Tier 2: Syntax-Aware AST Chunking
        ast_chunks = self._try_tier2_ast_chunking(raw_source, lines, file_path)
        if ast_chunks is not None:
            return ast_chunks

        # 3. Fallback to Tier 3: Intra-component deterministic line windowing with overlap
        return self._tier3_windowed_chunking(lines, file_path)

    def _try_tier2_ast_chunking(
        self,
        raw_source: str,
        lines: list[str],
        file_path: str,
    ) -> list[SourceChunk] | None:
        """Attempt syntax-aware AST chunking. Returns None if AST cannot be parsed or if nodes exceed budget."""
        try:
            tree = ast.parse(raw_source)
        except SyntaxError:
            # Fall back to Tier 3 on syntax errors
            return None

        total_lines = len(lines)
        body_nodes = tree.body
        if not body_nodes:
            return None

        # Step 2a: Identify shared preamble (module docstring, imports, constants)
        preamble_end_line = 0
        preamble_lines: list[tuple[int, str]] = []

        # Find initial imports, docstrings, or assignments before any class/function
        structural_indices: list[int] = []
        for idx, node in enumerate(body_nodes):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                structural_indices.append(idx)
            elif not structural_indices and hasattr(node, "end_lineno") and node.end_lineno is not None:
                preamble_end_line = max(preamble_end_line, node.end_lineno)

        if preamble_end_line > 0:
            for i in range(preamble_end_line):
                preamble_lines.append((i + 1, lines[i]))

        # Group structural units
        structural_units: list[tuple[int, int, str]] = []  # (start_line, end_line, desc)
        for idx in structural_indices:
            node = body_nodes[idx]
            s = node.lineno
            e = getattr(node, "end_lineno", node.lineno)
            name = getattr(node, "name", type(node).__name__)
            structural_units.append((s, e, f"{type(node).__name__}:{name}"))

        if not structural_units:
            return None

        # Check if any single structural unit exceeds the token budget on its own
        for s, e, _ in structural_units:
            rendered = render_source_lines(lines, s, e, file_path, total_lines, preamble_lines)
            if self.count_tokens(rendered) > self.token_budget:
                # A single class or function exceeds budget; fall back to Tier 3
                return None

        # Step 2b: Greedy deterministic grouping in ascending lexical order
        chunks: list[SourceChunk] = []
        current_start = structural_units[0][0]
        current_end = structural_units[0][1]
        current_units = [structural_units[0][2]]

        for s, e, desc in structural_units[1:]:
            test_rendered = render_source_lines(lines, current_start, e, file_path, total_lines, preamble_lines)
            if self.count_tokens(test_rendered) <= self.token_budget:
                current_end = e
                current_units.append(desc)
            else:
                # Close current chunk
                rendered = render_source_lines(
                    lines, current_start, current_end, file_path, total_lines, preamble_lines
                )
                chunk_raw = "".join(lines[current_start - 1 : current_end])
                chunks.append(
                    SourceChunk(
                        file_path=file_path,
                        chunk_index=len(chunks) + 1,
                        total_chunks=0,  # update later
                        start_line=current_start,
                        end_line=current_end,
                        total_lines=total_lines,
                        rendered_text=rendered,
                        raw_code=chunk_raw,
                        token_estimate=self.count_tokens(rendered),
                        tier=2,
                        scope_description="; ".join(current_units),
                    )
                )
                current_start = s
                current_end = e
                current_units = [desc]

        # Append last group
        rendered = render_source_lines(lines, current_start, current_end, file_path, total_lines, preamble_lines)
        chunk_raw = "".join(lines[current_start - 1 : current_end])
        chunks.append(
            SourceChunk(
                file_path=file_path,
                chunk_index=len(chunks) + 1,
                total_chunks=0,
                start_line=current_start,
                end_line=current_end,
                total_lines=total_lines,
                rendered_text=rendered,
                raw_code=chunk_raw,
                token_estimate=self.count_tokens(rendered),
                tier=2,
                scope_description="; ".join(current_units),
            )
        )

        # Invariant check: Ensure first chunk starts at line 1 (incorporate preamble if any gap)
        if chunks and chunks[0].start_line > 1:
            # Expand first chunk to start at line 1
            first = chunks[0]
            new_rendered = render_source_lines(lines, 1, first.end_line, file_path, total_lines)
            if self.count_tokens(new_rendered) <= self.token_budget:
                chunks[0] = SourceChunk(
                    file_path=file_path,
                    chunk_index=first.chunk_index,
                    total_chunks=0,
                    start_line=1,
                    end_line=first.end_line,
                    total_lines=total_lines,
                    rendered_text=new_rendered,
                    raw_code="".join(lines[0 : first.end_line]),
                    token_estimate=self.count_tokens(new_rendered),
                    tier=2,
                    scope_description=f"Preamble + {first.scope_description}",
                )
            else:
                return None  # Cannot cleanly bridge line 1, fallback to Tier 3

        # Invariant check: Ensure last chunk ends at total_lines
        if chunks and chunks[-1].end_line < total_lines:
            last = chunks[-1]
            new_rendered = render_source_lines(lines, last.start_line, total_lines, file_path, total_lines)
            if self.count_tokens(new_rendered) <= self.token_budget:
                chunks[-1] = SourceChunk(
                    file_path=file_path,
                    chunk_index=last.chunk_index,
                    total_chunks=0,
                    start_line=last.start_line,
                    end_line=total_lines,
                    total_lines=total_lines,
                    rendered_text=new_rendered,
                    raw_code="".join(lines[last.start_line - 1 : total_lines]),
                    token_estimate=self.count_tokens(new_rendered),
                    tier=2,
                    scope_description=f"{last.scope_description} + Trailing",
                )
            else:
                return None  # Cannot bridge end, fallback to Tier 3

        # Update total_chunks
        total_k = len(chunks)
        final_chunks: list[SourceChunk] = []
        for c in chunks:
            final_chunks.append(
                SourceChunk(
                    file_path=c.file_path,
                    chunk_index=c.chunk_index,
                    total_chunks=total_k,
                    start_line=c.start_line,
                    end_line=c.end_line,
                    total_lines=c.total_lines,
                    rendered_text=c.rendered_text,
                    raw_code=c.raw_code,
                    token_estimate=c.token_estimate,
                    tier=2,
                    scope_description=c.scope_description,
                    token_count_method=self.token_count_method,
                )
            )

        return final_chunks

    def _tier3_windowed_chunking(self, lines: list[str], file_path: str) -> list[SourceChunk]:
        """Tier 3: Deterministic sliding line window with fixed N=100 overlap."""
        total_lines = len(lines)
        overlap = min(self.tier3_overlap, total_lines // 2) if total_lines > 1 else 0

        chunks: list[SourceChunk] = []
        start_line = 1

        while start_line <= total_lines:
            # Binary search or scan for maximum end_line that fits budget
            low = start_line
            high = total_lines
            best_end = start_line

            while low <= high:
                mid = (low + high) // 2
                rendered = render_source_lines(lines, start_line, mid, file_path, total_lines)
                tokens = self.count_tokens(rendered)
                if tokens <= self.token_budget:
                    best_end = mid
                    low = mid + 1
                else:
                    high = mid - 1

            if (
                best_end == start_line
                and self.count_tokens(render_source_lines(lines, start_line, best_end, file_path, total_lines))
                > self.token_budget
            ):
                # Even a single line exceeds budget (extreme case)
                best_end = start_line

            rendered = render_source_lines(lines, start_line, best_end, file_path, total_lines)
            chunk_raw = "".join(lines[start_line - 1 : best_end])
            chunks.append(
                SourceChunk(
                    file_path=file_path,
                    chunk_index=len(chunks) + 1,
                    total_chunks=0,
                    start_line=start_line,
                    end_line=best_end,
                    total_lines=total_lines,
                    rendered_text=rendered,
                    raw_code=chunk_raw,
                    token_estimate=self.count_tokens(rendered),
                    tier=3,
                    scope_description=f"Window lines {start_line}-{best_end} (Tier 3, overlap={overlap})",
                )
            )

            if best_end >= total_lines:
                break

            # Advance start_line with overlap
            next_start = best_end - overlap + 1
            if next_start <= start_line:
                next_start = start_line + 1
            start_line = next_start

        # Finalize total_chunks
        total_k = len(chunks)
        final_chunks: list[SourceChunk] = []
        for c in chunks:
            final_chunks.append(
                SourceChunk(
                    file_path=c.file_path,
                    chunk_index=c.chunk_index,
                    total_chunks=total_k,
                    start_line=c.start_line,
                    end_line=c.end_line,
                    total_lines=c.total_lines,
                    rendered_text=c.rendered_text,
                    raw_code=c.raw_code,
                    token_estimate=c.token_estimate,
                    tier=3,
                    scope_description=c.scope_description,
                    token_count_method=self.token_count_method,
                )
            )

        return final_chunks
