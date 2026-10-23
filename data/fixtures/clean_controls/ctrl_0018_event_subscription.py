"""Clean Control Fixture: CTRL-0018
Paired with: CAND-0033 (Category 6: Authorization & Privilege Escalation)
Target Scope: Typing notification and event broadcast authorization
Intended Behavior: Checks that sender has active write permissions on target topic
before broadcasting notification, preventing unauthorized notification spoofing (CWE-863).
"""

from __future__ import annotations

from typing import Protocol


class TopicAuthorizationPolicy(Protocol):
    """Protocol for checking write access on stream/topic."""

    def can_write_to_topic(self, user_id: int, stream_id: int, topic_name: str) -> bool: ...


def can_send_typing_event(
    sender_id: int,
    stream_id: int,
    topic_name: str,
    policy: TopicAuthorizationPolicy,
) -> bool:
    """Authorize typing notification dispatch for verified active contributors."""
    if sender_id <= 0 or stream_id <= 0 or not topic_name.strip():
        return False

    return policy.can_write_to_topic(sender_id, stream_id, topic_name.strip())
