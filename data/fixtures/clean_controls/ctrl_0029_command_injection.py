"""Clean Control Fixture: CTRL-0029
Paired with: CAND-0023 (Category 2: Input Validation / Sanitization)
Target Scope: Host diagnostics ping execution
Intended Behavior: Passes validated arguments as token list with shell=False.
"""

from __future__ import annotations
import re
import subprocess

SAFE_HOSTNAME_RE = re.compile(r"^[a-zA-Z0-9.-]+$")

def run_network_diagnostic(target_host: str) -> str:
    """Run diagnostic safely passing discrete arguments."""
    if not SAFE_HOSTNAME_RE.match(target_host):
        raise ValueError("Invalid target hostname")
    res = subprocess.run(["ping", "-c", "1", target_host], shell=False, capture_output=True, text=True)
    return res.stdout
