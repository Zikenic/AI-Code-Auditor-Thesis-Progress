import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import io
import pytest
from chunk_consumer import process_stream_payload
from bounded_stream import StreamCapExceeded


def test_process_stream_payload_success():
    data = b"Hello, world!" * 100
    stream = io.BytesIO(data)
    result = process_stream_payload(stream, max_size_bytes=50_000)
    assert result == data


def test_process_stream_payload_exceeded_cap():
    huge_data = b"X" * 100_000
    stream = io.BytesIO(huge_data)
    with pytest.raises(StreamCapExceeded):
        process_stream_payload(stream, max_size_bytes=10_000)
