"""Clean Control Fixture: CTRL-0006
Paired with: CAND-0008 (Category 2: Input Validation / Regular Expression DoS)
Target Scope: Multipart boundary extraction and linear-time delimiter searching
Intended Behavior: Uses linear string search and size limits to parse multipart headers,
preventing catastrophic backtracking (ReDoS / CWE-1333).
"""

from __future__ import annotations


def parse_multipart_boundary(content_type_header: str) -> str | None:
    """Extract multipart boundary parameter without backtracking regular expressions."""
    if not content_type_header or len(content_type_header) > 1024:
        return None

    # Find boundary marker with bounded string operations
    marker = "boundary="
    idx = content_type_header.lower().find(marker)
    if idx == -1:
        return None

    rest = content_type_header[idx + len(marker) :].strip()
    if not rest:
        return None

    # Handle quoted boundary
    if rest.startswith('"'):
        end_quote = rest.find('"', 1)
        if end_quote != -1:
            boundary = rest[1:end_quote].strip()
            return boundary if (1 <= len(boundary) <= 70) else None
        return None

    # Unquoted boundary ends at semicolon or whitespace
    boundary = rest.split(";")[0].strip()
    return boundary if (1 <= len(boundary) <= 70) else None
