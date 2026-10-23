"""Clean Control Fixture: CTRL-0005
Paired with: CAND-0009 (Category 2: Input Validation / Cross-Site Scripting)
Target Scope: HTML template escaping and markup attribute sanitization
Intended Behavior: Correctly sanitizes user input before rendering inside HTML,
preventing Cross-Site Scripting (XSS / CWE-79).
"""

from __future__ import annotations

import html


def safe_render_comment(user_name: str, comment_text: str) -> str:
    """Safely format a user comment into HTML with strict entity escaping."""
    safe_name = html.escape(user_name.strip(), quote=True)
    safe_comment = html.escape(comment_text.strip(), quote=True)
    return f'<div class="comment"><strong>{safe_name}</strong>: <p>{safe_comment}</p></div>'


def sanitize_attribute_value(val: str) -> str:
    """Escape characters for safe inclusion in an HTML attribute value."""
    return html.escape(val, quote=True).replace("'", "&#x27;")
