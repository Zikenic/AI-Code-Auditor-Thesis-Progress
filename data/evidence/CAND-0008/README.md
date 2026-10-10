# CAND-0008: Bounded Reproducibility Evidence for python-multipart ReDoS

- **Candidate ID**: `CAND-0008`
- **Target Repository**: `Kludex/python-multipart` (https://github.com/Kludex/python-multipart)
- **Vulnerability Identifier**: CVE-2024-24762 / GHSA-2jv5-9r88-3w3p
- **Vulnerability Category**: Category 2 — Input Validation / Sanitization
- **Primary CWE**: CWE-1333 (Inefficient Regular Expression Complexity)
- **Alternative CWE Set**: `["CWE-400", "CWE-20"]`
- **Buggy Commit**: `d3d16dae4b061c34fe9d3c9081d9800c49fc1f7a`
- **Fixed Commit**: `20f0ef6b4e4caf7d69a667c54dff57fe467109a4`
- **Pre-Fix Locus**: `multipart/multipart.py:28-40` (`OPTION_RE` definition) and `parse_options_header` caller

---

## 1. Vulnerability Analysis & Regex Mechanics

In `multipart/multipart.py`, the header parameter parser used a regular expression compiled as:

```python
QUOTED_STR = rb'"(?:\\.|[^"])*"'
OPTION_RE = re.compile(
    rb"^;?\s*(?:([a-zA-Z0-9_]+)=)?(?:(?:" + QUOTED_STR + rb")|([^;]+))",
    re.VERBOSE,
)
```

When evaluating a Content-Type parameter with an unclosed opening quote followed by trailing backslashes:
`application/x-www-form-urlencoded; !="\\\\\\\\...`

The subpattern `(?:\\.|[^"])*` has two overlapping alternatives:
1. `\\.` matches any two characters starting with a backslash.
2. `[^"]` matches any character other than a double quote (which includes `\`).

Because the closing quote is missing, the regex engine fails to find a terminating quote and exhaustively backtracks across all valid partitions of the backslash sequence.

### Complexity Claim & Theoretical Consistency

> **Peer-Review-Grade Framing**: The timing measurements demonstrate **"experimentally observed exponential growth over the tested range"** ($N \in [20, 36]$).
>
> Over this range, the scaling factor is empirically consistent with $\approx \varphi^N$ (where the golden ratio $\varphi \approx 1.618$ reflects the theoretical branching factor of single-character `[^"]` and two-character `\\.` backslash partitions).
>
> We do not assert formal asymptotic lower or upper bounds, nor claim a formal mathematical proof of Fibonacci recurrence under real-world CPython NFA execution. Note that at very small $N$ (e.g. $N < 20$), constant Python interpreter and subprocess startup overhead dominates execution time, while for $N \ge 20$ catastrophic backtracking rapidly dominates.

---

## 2. Experimental Setup

The reproducibility harness (`reproduce_redos.py`) conducts isolated subprocess evaluations:
1. **Unmodified Upstream Packages**: Pinned revisions for buggy commit `d3d16dae` and fixed commit `20f0ef6b` reside under `revisions/buggy/multipart/` and `revisions/fixed/multipart/`.
2. **Subprocess Isolation**: Every timing measurement is run in an independent Python interpreter subprocess via `PYTHONPATH` redirection to eliminate process cache, JIT, or module state interference.
3. **Median-of-Five Protocol**: Each data point is evaluated across 5 consecutive subprocess runs; the reported metric is the median execution time.
4. **Hard Timeout Protection**: Subprocesses are bounded by a 10.0-second timeout to prevent runaway resource exhaustion.
5. **Direct & Framework Ingestion**: Measurements are taken on direct `parse_options_header()` calls as well as a standard WSGI `simple_app` handler mimicking server-side ingestion.

---

## 3. Empirical Results

Evaluated on Windows 10 (AMD64), Python 3.12 (CPython), 5 repetitions per point:

| $N$ (Backslashes) | Header Length | Buggy Median (Direct) | Fixed Median (Direct) | Direct Slowdown | Buggy Median (WSGI) | Fixed Median (WSGI) | WSGI Slowdown |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **20** | 58 chars | 0.000638 s | 0.000025 s | **25.0×** | 0.000643 s | 0.000026 s | **24.7×** |
| **24** | 62 chars | 0.004215 s | 0.000026 s | **164.0×** | 0.004217 s | 0.000026 s | **162.2×** |
| **28** | 66 chars | 0.028621 s | 0.000026 s | **1,096.6×** | 0.028622 s | 0.000026 s | **1,100.8×** |
| **30** | 68 chars | 0.074128 s | 0.000027 s | **2,735.3×** | 0.074211 s | 0.000027 s | **2,748.6×** |
| **32** | 70 chars | 0.195256 s | 0.000026 s | **7,538.8×** | 0.195310 s | 0.000026 s | **7,511.9×** |
| **34** | 72 chars | 0.503265 s | 0.000026 s | **19,135.5×** | 0.503348 s | 0.000026 s | **19,359.5×** |
| **36** | 74 chars | 1.338705 s | 0.000027 s | **50,517.2×** | 1.341120 s | 0.000027 s | **49,671.1×** |

### Observations:
1. **Exponential Growth**: Time roughly doubles every 2 backslashes ($\approx 1.618^2 = 2.62$). Increasing $N$ from 20 to 36 (a 16-character difference in header payload) increases execution time from 0.6 ms to 1.34 seconds (>2,000× increase in processing time).
2. **Fixed Baseline Invariance**: The fixed revision (which replaced `OPTION_RE` with the standard library `email.message.Message`) processes the payload in constant time $\approx 26\ \mu\text{s}$ regardless of payload length.
3. **Slowdown Factor**: At $N=36$, the vulnerable implementation experiences an observed slowdown exceeding **50,000×**.
4. **Reproducer Status**: The defect is conclusively verified and reproduced with `reproducer_status = "executed_confirmed"`.

---

## 4. Evidence Artifact Inventory

- `reproduce_redos.py`: Self-contained reproduction runner with on-demand upstream cloning and SHA-256 verification.
- `results.json`: Full machine-readable timing runs, SHA-256 source verification records, and metadata.
- `stdout.log`: Console log from test suite execution.
- `environment.json`: System and runtime environment capture.
- `ghsa_response.json`: Authoritative GitHub Advisory API snapshot for GHSA-2jv5-9r88-3w3p.
- `revisions/buggy/` & `revisions/fixed/`: Dynamically extracted from upstream commits `d3d16dae` and `20f0ef6b` (gitignored to prevent repository bloat; verified via SHA-256 against upstream git objects on every run).
