"""Clean Control Fixture: CTRL-0024
Paired with: CAND-0012 (Category 2: Input Validation / Sanitization)
Target Scope: Webhook URL retrieval and HTTP dispatch
Intended Behavior: Enforces protocol whitelist and blocks RFC1918 private IPs.
"""

from __future__ import annotations
import ipaddress
import socket
import urllib.parse
import urllib.request

def is_safe_webhook_url(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(host))
        return not (ip.is_private or ip.is_loopback or ip.is_link_local)
    except Exception:
        return False

def fetch_webhook_payload(target_url: str) -> str:
    if not is_safe_webhook_url(target_url):
        raise ValueError("Untrusted or private IP target URL")
    req = urllib.request.Request(target_url)
    with urllib.request.urlopen(req, timeout=5) as response:
        return response.read().decode("utf-8")
