"""Streaming chunk consumer reading payloads into processing buffer."""

from __future__ import annotations

from typing import BinaryIO
from bounded_stream import BoundedStreamReader, StreamCapExceeded


def process_stream_payload(raw_stream: BinaryIO, max_size_bytes: int = 500_000) -> bytes:
    """Consume and accumulate streamed bytes with bounded memory guarantees.

    Wraps the incoming stream with `bounded_stream.BoundedStreamReader` to protect
    against denial of service caused by unbounded memory allocation or infinite streams.
    """
    reader = BoundedStreamReader(raw_stream, max_total_bytes=max_size_bytes)
    buffer = bytearray()

    while True:
        chunk = reader.read_chunk(chunk_size=8192)
        if not chunk:
            break
        buffer.extend(chunk)

    return bytes(buffer)
