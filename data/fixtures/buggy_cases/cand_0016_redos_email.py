"""Buggy Fixture: CAND-0016
Category 2: Input Validation / Sanitization
Primary CWE: CWE-1333 (Inefficient Regular Expression Complexity - ReDoS)
"""

from __future__ import annotations
import re

VULNERABLE_EMAIL_PATTERN = re.compile(r"^([a-zA-Z0-9]+[._-]?)+@([a-zA-Z0-9]+[.-]?)+\.[a-zA-Z]{2,}$")

def validate_user_email(email_str: str) -> bool:
    """Validate user email string using regular expression."""
    return bool(VULNERABLE_EMAIL_PATTERN.match(email_str))
