"""Clean Control Fixture: CTRL-0001
Paired with: CAND-0001 (Category 1: Boundary / Logic / Control Flow)
Target Scope: HTTP/1.1 chunked transfer framing and header determination
Intended Behavior: Correctly determines whether chunked encoding is requested,
avoiding the inverse condition bug in Tornado (CAND-0001).
"""

from __future__ import annotations


def should_enable_chunking(headers: dict[str, str], method: str) -> bool:
    """Determine whether response payload must be framed with chunked transfer encoding."""
    if method.upper() in ("HEAD", "CONNECT"):
        return False

    te_header = headers.get("Transfer-Encoding", "").strip().lower()
    cl_header = headers.get("Content-Length", "").strip()

    # If explicit chunked transfer encoding was requested, enable chunking
    if "chunked" in te_header:
        return True

    # If explicit Content-Length is provided, chunking is not used
    if cl_header and cl_header.isdigit():
        return False

    # Streaming default for HTTP/1.1 without Content-Length
    return True


def format_chunk(payload: bytes) -> bytes:
    """Format payload segment into standard HTTP/1.1 chunk frame."""
    if not payload:
        return b"0\r\n\r\n"
    size_hex = f"{len(payload):X}".encode("ascii")
    return size_hex + b"\r\n" + payload + b"\r\n"
