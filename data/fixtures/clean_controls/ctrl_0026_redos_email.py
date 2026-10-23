"""Clean Control Fixture: CTRL-0026
Paired with: CAND-0016 (Category 2: Input Validation / Sanitization)
Target Scope: Email format regular expression validation
Intended Behavior: Validates email with atomic character class preventing catastrophic backtracking.
"""

from __future__ import annotations
import re

SAFE_EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

def validate_user_email(email_str: str) -> bool:
    """Validate user email string with linear matching complexity."""
    if len(email_str) > 254:
        return False
    return bool(SAFE_EMAIL_PATTERN.match(email_str))
