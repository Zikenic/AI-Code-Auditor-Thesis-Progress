"""Reproducible local benchmark for PBKDF2-HMAC-SHA256 input size and iteration overhead.

NOTE ON PROVENANCE AND METHODOLOGICAL LIMITATIONS:
1. Historical Timing Provenance:
   The timing figures in the initial reconciliation report were generated via an ad-hoc inline
   Python command during an interactive shell session. Their raw timing vectors and platform
   telemetry were not preserved in a versioned artifact.
2. Narrow Scope:
   This benchmark measures strictly the in-process execution time of `hashlib.pbkdf2_hmac`
   (and string UTF-8 encoding) using pre-allocated inputs in local memory.
3. What This Does NOT Measure:
   - HTTP transport latency, network streaming, or reverse-proxy buffering.
   - Web framework (e.g. FastAPI / Flask / Django) body parsing or deserialization.
   - Memory allocation costs for multi-megabyte payloads in untrusted client requests.
   - Concurrent request load, thread exhaustion, or system denial of service.
4. Technical Scope:
   This benchmark demonstrates solely the cryptographic property defined in RFC 2104 and
   FIPS 198-1: when HMAC receives a key longer than the block size (64 bytes for SHA-256),
   it pre-hashes the key with SHA-256 down to 32 bytes ONCE before commencing the PBKDF2
   iteration loops. It does NOT prove that accepting unbounded payloads from remote clients is safe.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "data" / "results" / "context_ablation_pilot" / "pbkdf2_benchmark_measurements.json"

CONFIGURATIONS = [
    {
        "name": "typical_password_100k",
        "description": "Baseline: 12-byte password, 100,000 iterations",
        "payload_bytes_len": 12,
        "iterations": 100_000,
        "payload_gen": lambda: "P@ssw0rd123!",
    },
    {
        "name": "large_password_1mb_100k",
        "description": "Oversized payload: 1 Megabyte string, 100,000 iterations",
        "payload_bytes_len": 1_000_000,
        "iterations": 100_000,
        "payload_gen": lambda: "A" * 1_000_000,
    },
    {
        "name": "extreme_password_10mb_100k",
        "description": "Extreme payload: 10 Megabytes string, 100,000 iterations",
        "payload_bytes_len": 10_000_000,
        "iterations": 100_000,
        "payload_gen": lambda: "A" * 10_000_000,
    },
    {
        "name": "owasp_hardened_600k",
        "description": "OWASP FIPS-140 recommended work factor: 12-byte password, 600,000 iterations",
        "payload_bytes_len": 12,
        "iterations": 600_000,
        "payload_gen": lambda: "P@ssw0rd123!",
    },
]

NUM_REPETITIONS = 10
WARMUP_RUNS = 1
STATIC_SALT = b"0123456789abcdef0123456789abcdef"


def run_benchmark() -> dict:
    results = {
        "benchmark_metadata": {
            "timestamp_utc": datetime.now(UTC).isoformat(),
            "python_version": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "num_repetitions": NUM_REPETITIONS,
            "warmup_runs": WARMUP_RUNS,
            "methodology_notes": [
                "Payload strings are pre-allocated in memory before timing starts to isolate hashing/encoding from garbage collection",
                "Timing measures UTF-8 encoding of pre-allocated string + hashlib.pbkdf2_hmac execution using time.perf_counter()",
                "Does NOT include HTTP transport, network framing, or server request body limits",
            ],
        },
        "measurements": [],
    }

    for cfg in CONFIGURATIONS:
        print(f"Running benchmark for {cfg['name']}...")
        payload_str = cfg["payload_gen"]()
        iterations = cfg["iterations"]

        # Warmup run (not included in statistics)
        for _ in range(WARMUP_RUNS):
            _ = hashlib.pbkdf2_hmac("sha256", payload_str.encode("utf-8"), STATIC_SALT, iterations=iterations)

        # Timed repetitions
        timings_ms: list[float] = []
        for _ in range(NUM_REPETITIONS):
            t0 = time.perf_counter()
            _ = hashlib.pbkdf2_hmac("sha256", payload_str.encode("utf-8"), STATIC_SALT, iterations=iterations)
            t1 = time.perf_counter()
            timings_ms.append((t1 - t0) * 1000.0)

        n = len(timings_ms)
        mean_ms = sum(timings_ms) / n
        variance = sum((x - mean_ms) ** 2 for x in timings_ms) / (n - 1)
        stdev_ms = math.sqrt(variance)

        results["measurements"].append({
            "name": cfg["name"],
            "description": cfg["description"],
            "payload_size_bytes": cfg["payload_bytes_len"],
            "iterations": iterations,
            "raw_timings_ms": timings_ms,
            "mean_ms": round(mean_ms, 2),
            "stdev_ms": round(stdev_ms, 2),
            "min_ms": round(min(timings_ms), 2),
            "max_ms": round(max(timings_ms), 2),
        })

    return results


def main():
    data = run_benchmark()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Benchmark results successfully saved to: {OUTPUT_PATH}")
    for m in data["measurements"]:
        print(f"  {m['name']}: {m['mean_ms']} ms ± {m['stdev_ms']} ms (min={m['min_ms']}, max={m['max_ms']})")


if __name__ == "__main__":
    main()
