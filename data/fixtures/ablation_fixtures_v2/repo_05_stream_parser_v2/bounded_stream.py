"""Stream reader wrapper enforcing strict length and chunk boundaries."""

from __future__ import annotations

from typing import BinaryIO


class StreamCapExceeded(ValueError):
    """Raised when stream byte consumption exceeds maximum safety limit."""
    pass


class BoundedStreamReader:
    """Wraps a binary stream with strict cumulative byte read and iteration limits.

    Protects downstream parsers against infinite loops, zip bombs, and unbounded memory DoS.
    """

    def __init__(self, stream: BinaryIO, max_total_bytes: int = 1_000_000, max_chunks: int = 500):
        self.stream = stream
        self.max_total_bytes = max_total_bytes
        self.max_chunks = max_chunks
        self.total_bytes_read = 0
        self.chunks_read = 0

    def read_chunk(self, chunk_size: int = 4096) -> bytes:
        """Read next chunk, enforcing both per-chunk and cumulative safety caps."""
        if self.chunks_read >= self.max_chunks:
            raise StreamCapExceeded(f"Exceeded maximum allowed stream chunks ({self.max_chunks})")

        data = self.stream.read(chunk_size)
        if not data:
            return b""

        self.chunks_read += 1
        self.total_bytes_read += len(data)
        if self.total_bytes_read > self.max_total_bytes:
            raise StreamCapExceeded(
                f"Stream exceeded safety limit: {self.total_bytes_read} bytes > {self.max_total_bytes} bytes"
            )

        return data
