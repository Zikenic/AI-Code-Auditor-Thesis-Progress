"""Buggy Fixture: CAND-0023
Category 2: Input Validation / Sanitization
Primary CWE: CWE-78 (OS Command Injection)
"""

from __future__ import annotations
import subprocess

def run_network_diagnostic(target_host: str) -> str:
    """Run ping against user-specified target host."""
    cmd = f"ping -c 1 {target_host}"
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return res.stdout
